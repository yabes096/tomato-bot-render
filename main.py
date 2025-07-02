import discord
from discord.ext import commands
import requests
import matplotlib.pyplot as plt
from io import BytesIO
import numpy as np
from difflib import get_close_matches
from sklearn.linear_model import LinearRegression
import feedparser
from keep_alive import keep_alive
import os

TOKEN = os.getenv("TOKEN")
PREFIX = '.'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

alert_data = {}
coin_list_cache = []

# ===== FUNGSI BANTU =====


def update_coin_list():
    global coin_list_cache
    try:
        coin_list_cache = requests.get(
            "https://api.coingecko.com/api/v3/coins/list").json()
    except:
        coin_list_cache = []


def cari_id_coin(symbol):
    if not coin_list_cache:
        update_coin_list()
    symbol_lower = symbol.lower()
    for coin in coin_list_cache:
        if coin['symbol'].lower() == symbol_lower or coin['id'].lower(
        ) == symbol_lower or coin['name'].lower() == symbol_lower:
            return coin['id'], None
    symbols = [c['symbol'].lower() for c in coin_list_cache] + [
        c['id'].lower() for c in coin_list_cache
    ] + [c['name'].lower() for c in coin_list_cache]
    suggestion = get_close_matches(symbol_lower, symbols, n=1)
    if suggestion:
        return None, suggestion[0]
    return None, None


def get_price(coin_id):
    try:
        res = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        ).json()
        return res.get(coin_id, {}).get('usd')
    except:
        return None


def get_market_chart(coin_id, days):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {'vs_currency': 'usd', 'days': days}
        data = requests.get(url, params=params).json()
        return data['prices']  # List of [timestamp, price]
    except:
        return None


async def cek_alert(channel, cid, harga):
    if cid not in alert_data:
        return
    batas = alert_data[cid]
    if harga >= batas['atas']:
        await channel.reply(
            f"🚨 {cid.upper()} naik di atas ${batas['atas']}! Sekarang: ${harga:.4f}"
        )
        del alert_data[cid]
    elif harga <= batas['bawah']:
        await channel.reply(
            f"🚨 {cid.upper()} turun di bawah ${batas['bawah']}! Sekarang: ${harga:.4f}"
        )
        del alert_data[cid]


# ===== PERINTAH BOT =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    lines = message.content.strip().splitlines()
    for line in lines:
        if line.startswith(PREFIX):
            fake_message = message
            fake_message.content = line.strip()
            ctx = await bot.get_context(fake_message)
            await bot.process_commands(fake_message)


@bot.command()
async def help(ctx):
    async with ctx.typing():
        embed = discord.Embed(title="📘 Panduan Bot Tomato",
                              color=discord.Color.blue())
        embed.add_field(name=".harga <symbol>",
                        value="Harga coin terkini",
                        inline=False)
        embed.add_field(name=".info <symbol>",
                        value="Info lengkap coin",
                        inline=False)
        embed.add_field(name=".grafik <symbol>",
                        value="Grafik + prediksi harga besok",
                        inline=False)
        embed.add_field(name=".setalert <symbol> <bawah> <atas>",
                        value="Set alert harga",
                        inline=False)
        embed.add_field(name=".listalert",
                        value="Lihat semua alert",
                        inline=False)
        embed.add_field(name=".hapusalert <symbol>",
                        value="Hapus alert coin",
                        inline=False)
        embed.add_field(name=".top10",
                        value="Top 10 coin berdasarkan market cap",
                        inline=False)
        embed.add_field(name=".convert <from> <to> <jumlah>",
                        value="Konversi antar coin",
                        inline=False)
        embed.add_field(name=".fiatcurrency <coin> <currency> <jumlah>",
                        value="Crypto <-> Fiat",
                        inline=False)
        embed.add_field(name=".convertcurrency <from> <to> <jumlah>",
                        value="Konversi antar mata uang negara",
                        inline=False)
        embed.add_field(name=".dominance",
                        value="Dominasi pasar crypto",
                        inline=False)
        embed.add_field(name=".trending",
                        value="Coin yang sedang trending",
                        inline=False)
        embed.add_field(name=".marketmovement <symbol...>",
                        value="Pergerakan market coin pilihanmu",
                        inline=False)
        embed.add_field(name=".cryptonews",
                        value="Berita terbaru seputar crypto",
                        inline=False)
        embed.add_field(name=".feargreed",
                        value="Indeks kecemasan pasar crypto",
                        inline=False)
        embed.add_field(name=".topchange",
                        value="Top 5 coin naik & turun 24 jam",
                        inline=False)
        embed.add_field(name=".profit <symbol> <beli> <jual>",
                        value="Hitung keuntungan/kerugian",
                        inline=False)
        embed.add_field(name=".kick @user [alasan]",
                        value="Keluarkan member (admin only)",
                        inline=False)

        await ctx.reply(embed=embed)


@bot.command()
async def harga(ctx, symbol):
    async with ctx.typing():
        coin_id, suggestion = cari_id_coin(symbol)
        if coin_id:
            price = get_price(coin_id)
            if price:
                await ctx.reply(
                    f"Harga {symbol.upper()} saat ini: ${price:.4f}")
            else:
                await ctx.reply("Gagal mengambil harga.")
        elif suggestion:
            await ctx.reply(
                f"Coin tidak ditemukan. Mungkin maksudmu: `{suggestion}`?")
        else:
            await ctx.reply("Coin tidak ditemukan.")


@bot.command()
async def info(ctx, symbol):
    async with ctx.typing():
        coin_id, suggestion = cari_id_coin(symbol)
        if coin_id:
            try:
                url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                data = requests.get(url).json()
                name = data.get("name", "Unknown")
                description = data.get("description", {}).get(
                    "en", "No description").split(".")[0] + "."
                market_cap = data.get("market_data", {}).get("market_cap",
                                                             {}).get("usd", 0)
                price = data.get("market_data", {}).get("current_price",
                                                        {}).get("usd", 0)
                homepage = data.get("links", {}).get("homepage", [""])[0]

                embed = discord.Embed(title=f"{name} ({symbol.upper()})",
                                      description=description,
                                      color=discord.Color.green())
                embed.add_field(name="Harga Sekarang",
                                value=f"${price:,.4f}",
                                inline=True)
                embed.add_field(name="Market Cap",
                                value=f"${market_cap:,.0f}",
                                inline=True)
                if homepage:
                    embed.add_field(name="Website",
                                    value=homepage,
                                    inline=False)

                await ctx.reply(embed=embed)
            except Exception as e:
                await ctx.reply("Gagal mengambil data coin.")
                print("Error:", e)
        elif suggestion:
            await ctx.reply(
                f"Coin tidak ditemukan. Mungkin maksudmu: `{suggestion}`?")
        else:
            await ctx.reply("Coin tidak ditemukan.")


@bot.command()
async def grafik(ctx, symbol):
    async with ctx.typing():
        coin_id, suggestion = cari_id_coin(symbol)
        if not coin_id:
            if suggestion:
                await ctx.reply(
                    f"Coin tidak ditemukan. Mungkin maksudmu: `{suggestion}`?")
            else:
                await ctx.reply("Coin tidak ditemukan.")
            return

        data_24h = get_market_chart(coin_id, 1)
        data_7d = get_market_chart(coin_id, 7)

        if not data_24h or not data_7d:
            await ctx.reply("Gagal mengambil data grafik.")
            return

        # ===== Data 24 JAM =====
        timestamps_24h = [p[0] for p in data_24h]
        prices_24h = [p[1] for p in data_24h]

        # ===== Data 7 HARI + Prediksi =====
        timestamps_7d = [p[0] for p in data_7d]
        prices_7d = [p[1] for p in data_7d]

        x = np.arange(len(prices_7d)).reshape(-1, 1)
        y = np.array(prices_7d)

        model = LinearRegression()
        model.fit(x, y)
        pred_tomorrow = model.predict([[len(prices_7d)]])

        # ===== Plot =====
        plt.figure(figsize=(14, 6))

        # Subplot 1: Grafik 24 jam
        plt.subplot(1, 2, 1)
        plt.plot(prices_24h, label="Harga per jam (24 jam)")
        plt.title(f"{symbol.upper()} - 24 Jam Terakhir")
        plt.xlabel("Jam")
        plt.ylabel("Harga (USD)")
        plt.grid(True)
        plt.legend()

        # Subplot 2: Grafik 7 hari + prediksi
        plt.subplot(1, 2, 2)
        plt.plot(prices_7d, label="Harga harian (7 hari)")
        plt.plot(len(prices_7d),
                 pred_tomorrow[0],
                 'ro',
                 label="Prediksi Besok")
        plt.title(f"{symbol.upper()} - 7 Hari & Prediksi")
        plt.xlabel("Hari")
        plt.ylabel("Harga (USD)")
        plt.grid(True)
        plt.legend()

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()

        await ctx.reply(file=discord.File(fp=buffer, filename='grafik.png'))


@bot.command()
async def setalert(ctx, symbol, bawah: float, atas: float):
    coin_id, suggestion = cari_id_coin(symbol)
    if not coin_id:
        if suggestion:
            await ctx.reply(
                f"Coin tidak ditemukan. Mungkin maksudmu: `{suggestion}`?")
        else:
            await ctx.reply("Coin tidak ditemukan.")
        return

    alert_data[coin_id] = {'bawah': bawah, 'atas': atas}
    await ctx.reply(
        f"🔔 Alert untuk {symbol.upper()} disetel: bawah ${bawah}, atas ${atas}"
    )


@bot.command()
async def listalert(ctx):
    async with ctx.typing():
        if not alert_data:
            await ctx.reply("Tidak ada alert aktif.")
            return

        msg = "**Daftar Alert Aktif:**\n"
        for cid, val in alert_data.items():
            msg += f"- {cid.upper()}: bawah ${val['bawah']}, atas ${val['atas']}\n"
        await ctx.reply(msg)


@bot.command()
async def hapusalert(ctx, symbol):
    async with ctx.typing():
        coin_id, suggestion = cari_id_coin(symbol)
        if coin_id in alert_data:
            del alert_data[coin_id]
            await ctx.reply(f"✅ Alert untuk {symbol.upper()} telah dihapus.")
        else:
            await ctx.reply(f"⚠️ Tidak ada alert untuk {symbol.upper()}.")


@bot.command()
async def top10(ctx):
    async with ctx.typing():
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 10,
                'page': 1
            }
            data = requests.get(url, params=params).json()

            embed = discord.Embed(title="📊 Top 10 Coin Berdasarkan Market Cap",
                                  color=discord.Color.gold())
            for coin in data:
                name = f"{coin['name']} ({coin['symbol'].upper()})"
                price = f"${coin['current_price']:,.2f}"
                cap = f"${coin['market_cap']:,.0f}"
                embed.add_field(name=name,
                                value=f"Harga: {price} | Market Cap: {cap}",
                                inline=False)

            await ctx.reply(embed=embed)
        except:
            await ctx.reply("Gagal mengambil data Top 10.")


@bot.command()
async def convert(ctx, from_symbol, to_symbol, jumlah: float):
    async with ctx.typing():
        from_id, _ = cari_id_coin(from_symbol)
        to_id, _ = cari_id_coin(to_symbol)

        if not from_id or not to_id:
            await ctx.reply("Coin tidak ditemukan.")
            return

        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': f"{from_id},{to_id}", 'vs_currencies': 'usd'}
            prices = requests.get(url, params=params).json()

            usd_from = prices[from_id]['usd']
            usd_to = prices[to_id]['usd']
            hasil = (jumlah * usd_from) / usd_to

            await ctx.reply(
                f"{jumlah} {from_symbol.upper()} ≈ {hasil:.6f} {to_symbol.upper()}"
            )
        except:
            await ctx.reply("Gagal konversi.")


@bot.command()
async def fiatcurrency(ctx, coin_symbol, currency, jumlah: float):
    async with ctx.typing():
        coin_id, _ = cari_id_coin(coin_symbol)
        currency = currency.lower()

        if not coin_id:
            await ctx.reply("Coin tidak ditemukan.")
            return

        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {'ids': coin_id, 'vs_currencies': currency}
            data = requests.get(url, params=params).json()

            rate = data[coin_id][currency]
            hasil = jumlah * rate
            await ctx.reply(
                f"{jumlah} {coin_symbol.upper()} ≈ {hasil:.2f} {currency.upper()}"
            )
        except:
            await ctx.reply("Gagal konversi.")


@bot.command()
async def convertcurrency(ctx, from_code: str, to_code: str, amount: float):
    async with ctx.typing():
        from_code = from_code.lower()
        to_code = to_code.lower()

        try:
            url = "https://api.coingecko.com/api/v3/exchange_rates"
            response = requests.get(url, timeout=5)
            data = response.json().get("rates", {})

            if from_code not in data or to_code not in data:
                await ctx.reply(
                    "⚠️ Kode mata uang tidak ditemukan.\n"
                    "Gunakan kode seperti `btc`, `eth`, `usd`, `eur`, dll.\n"
                    "Ketik `.listcurrencies` untuk melihat semua kode yang tersedia."
                )
                return

            from_rate = data[from_code]["value"]
            to_rate = data[to_code]["value"]
            result = (amount * from_rate) / to_rate

            await ctx.reply(
                f"{amount} {from_code.upper()} ≈ {result:,.6f} {to_code.upper()}"
            )

        except requests.exceptions.Timeout:
            await ctx.reply(
                "⏱️ Timeout saat menghubungi CoinGecko. Silakan coba lagi.")
        except Exception as e:
            await ctx.reply("❌ Terjadi kesalahan saat memproses konversi.")


@bot.command()
async def dominance(ctx):
    async with ctx.typing():
        try:
            url = "https://api.coingecko.com/api/v3/global"
            data = requests.get(url).json()["data"]

            dominance_data = data["market_cap_percentage"]

            # Ambil 7 coin teratas berdasarkan persentase dominasi
            top7 = sorted(dominance_data.items(),
                          key=lambda x: x[1],
                          reverse=True)[:7]

            embed = discord.Embed(title="📊 Dominasi 7 Crypto Teratas",
                                  color=discord.Color.dark_blue())
            for coin_id, percentage in top7:
                embed.add_field(name=coin_id.upper(),
                                value=f"{percentage:.2f}%",
                                inline=True)

            await ctx.reply(embed=embed)

        except Exception as e:
            print("❌ Error di dominance:", e)
            await ctx.reply("⚠️ Gagal mengambil data dominasi pasar.")


@bot.command()
async def trending(ctx):
    async with ctx.typing():
        try:
            url = "https://api.coingecko.com/api/v3/search/trending"
            data = requests.get(url).json()["coins"]

            embed = discord.Embed(title="📈 Coin Trending Saat Ini",
                                  color=discord.Color.purple())
            for i, item in enumerate(data, 1):
                coin = item["item"]
                name = f"{coin['name']} ({coin['symbol'].upper()})"
                rank = coin["market_cap_rank"] or "N/A"
                embed.add_field(name=f"{i}. {name}",
                                value=f"Rank: {rank}",
                                inline=False)

            await ctx.reply(embed=embed)
        except:
            await ctx.reply("Gagal mengambil data trending.")


@bot.command()
async def marketmovement(ctx, *symbols):
    async with ctx.typing():
        if not symbols:
            await ctx.reply(
                "❗ Contoh penggunaan: `.marketmovement btc eth sol`")
            return

        # Ambil ID Coin dari simbol
        coin_ids = []
        invalid = []
        for symbol in symbols:
            coin_id, suggestion = cari_id_coin(symbol)
            if coin_id:
                coin_ids.append(coin_id)
            elif suggestion:
                await ctx.reply(
                    f"⚠️ `{symbol}` tidak ditemukan. Mungkin maksudmu: `{suggestion}`?"
                )
                return
            else:
                invalid.append(symbol)

        if not coin_ids:
            await ctx.reply("❌ Semua coin tidak valid.")
            return

        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {'vs_currency': 'usd', 'ids': ','.join(coin_ids)}
            data = requests.get(url, params=params).json()

            embed = discord.Embed(title="📉 Pergerakan Market",
                                  color=discord.Color.orange())
            for coin in data:
                name = f"{coin['name']} ({coin['symbol'].upper()})"
                change = coin.get("price_change_percentage_24h", 0)
                price = coin.get("current_price", 0)
                embed.add_field(
                    name=name,
                    value=f"Harga: ${price:.2f} | 24h: {change:+.2f}%",
                    inline=False)

            await ctx.reply(embed=embed)

        except Exception as e:
            print("❌ Error marketmovement:", e)
            await ctx.reply("⚠️ Gagal mengambil data market.")


@bot.command()
async def topchange(ctx):
    async with ctx.typing():
        try:
            # Fetch Top 5 Gainers
            gainers_url = "https://api.coingecko.com/api/v3/coins/markets"
            gainers_params = {
                'vs_currency': 'usd',
                'order': 'price_change_percentage_24h_desc',
                'per_page': 5,
                'page': 1,
                'price_change_percentage': '24h'
            }
            gainers_data = requests.get(gainers_url,
                                        params=gainers_params).json()

            # Fetch Top 5 Losers
            losers_url = "https://api.coingecko.com/api/v3/coins/markets"
            losers_params = {
                'vs_currency': 'usd',
                'order': 'price_change_percentage_24h_asc',
                'per_page': 5,
                'page': 1,
                'price_change_percentage': '24h'
            }
            losers_data = requests.get(losers_url, params=losers_params).json()

            # Build Embed
            embed = discord.Embed(title="📊 Top Gainers & Losers (24 Jam)",
                                  color=discord.Color.random())

            # Gainers Section
            gainers_text = ""
            for coin in gainers_data:
                gainers_text += f"🟢 **{coin['name']} ({coin['symbol'].upper()})**\n"
                gainers_text += f"Harga: ${coin['current_price']:,.4f} (+{coin['price_change_percentage_24h']:.2f}%)\n"
            embed.add_field(name="📈 Top 5 Gainers",
                            value=gainers_text,
                            inline=False)

            # Losers Section
            losers_text = ""
            for coin in losers_data:
                losers_text += f"🔴 **{coin['name']} ({coin['symbol'].upper()})**\n"
                losers_text += f"Harga: ${coin['current_price']:,.4f} ({coin['price_change_percentage_24h']:.2f}%)\n"
            embed.add_field(name="📉 Top 5 Losers",
                            value=losers_text,
                            inline=False)

            await ctx.reply(embed=embed)

        except Exception as e:
            print("❌ Error topchange:", e)
            await ctx.reply("⚠️ Gagal mengambil data gainers/losers.")


@bot.command()
async def feargreed(ctx):
    async with ctx.typing():
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url)
            data = response.json()

            index = data['data'][0]
            value = index['value']
            value_classification = index['value_classification']
            timestamp = index['timestamp']

            embed = discord.Embed(
                title="😨📈 Crypto Fear & Greed Index",
                color=discord.Color.from_str("#f39c12") if value_classification
                == "Fear" else discord.Color.from_str("#2ecc71"))
            embed.add_field(name="Indeks", value=f"{value} / 100", inline=True)
            embed.add_field(name="Kondisi",
                            value=value_classification,
                            inline=True)
            embed.set_footer(text="Sumber: alternative.me")

            await ctx.reply(embed=embed)

        except Exception as e:
            print("❌ Error feargreed:", e)
            await ctx.reply("⚠️ Gagal mengambil data Fear & Greed Index.")


@bot.command()
async def cryptonews(ctx):
    async with ctx.typing():
        try:
            # Feed alternatif, bisa ganti ke Cointelegraph atau Bitcoin News jika mau
            feed = feedparser.parse("https://news.bitcoin.com/feed/")

            if not feed.entries:
                await ctx.reply("❗ Tidak ada berita tersedia saat ini.")
                return

            embed = discord.Embed(title="📰 Berita Crypto Terbaru",
                                  color=discord.Color.blue())
            for entry in feed.entries[:5]:
                title = entry.title
                link = entry.link
                embed.add_field(name=title, value=link, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            print("❌ Error di cryptonews:", e)
            await ctx.reply("⚠️ Gagal mengambil berita.")


@bot.command()
async def profit(ctx, symbol, harga_beli: float, harga_jual: float):
    async with ctx.typing():
        selisih = harga_jual - harga_beli
        persen = (selisih / harga_beli) * 100

        if persen >= 0:
            await ctx.reply(f"✅ Keuntungan: +{persen:.2f}% (${selisih:.2f})")
        else:
            await ctx.reply(f"❌ Kerugian: {persen:.2f}% (${selisih:.2f})")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, jumlah: int = 100):
    if jumlah > 100:
        await ctx.reply("❌ Maksimal bisa hapus 100 pesan sekaligus.")
        return

    await ctx.channel.purge(limit=jumlah + 1
                            )  # +1 untuk menghapus pesan command juga
    await ctx.send(f"✅ {jumlah} pesan berhasil dihapus.", delete_after=5)


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Tanpa alasan"):
    async with ctx.typing():
        try:
            await member.kick(reason=reason)
            await ctx.reply(
                f"👢 {member.mention} telah dikeluarkan. Alasan: {reason}")
        except:
            await ctx.reply("Gagal mengeluarkan member.")


from keep_alive import keep_alive

keep_alive()

bot.run(TOKEN)
