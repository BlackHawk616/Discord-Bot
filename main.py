import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import sqlite3
import random
import string

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Database setup
conn = sqlite3.connect('flight_booking.db')
c = conn.cursor()

# Create the bookings table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS bookings (
                ticket_id TEXT PRIMARY KEY,
                name TEXT,
                age INTEGER,
                passport TEXT,
                from_country TEXT,
                to_country TEXT,
                category TEXT,
                price INTEGER,
                departure_date TEXT,
                arrival_date TEXT
            )''')

# Dictionary to store temporary data for modals
temp_data = {}

# Function to generate a unique ticket ID
def generate_ticket_id():
    return f"{random.randint(1000, 9999)}{random.choice(string.ascii_uppercase)}{random.choice(string.ascii_uppercase)}{random.randint(0, 9)}{random.choice(string.ascii_uppercase)}"

# Modal for Flight Ticket Booking
# First Modal for basic passenger details
class BasicDetailsModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="✈️ Basic Passenger Details")
        self.user_id = user_id

        self.name = TextInput(label="Passenger Name", placeholder="Enter your name", required=True)
        self.age = TextInput(label="Age", placeholder="Enter your age", required=True)
        self.passport = TextInput(label="Passport Number", placeholder="Enter passport number", required=True)
        self.from_country = TextInput(label="Departure Country", placeholder="Enter departure country", required=True)
        self.to_country = TextInput(label="Destination Country", placeholder="Enter destination country", required=True)

        self.add_item(self.name)
        self.add_item(self.age)
        self.add_item(self.passport)
        self.add_item(self.from_country)
        self.add_item(self.to_country)

    async def on_submit(self, interaction: discord.Interaction):
        # Store details in the temp data
        temp_data[self.user_id] = {
            "name": self.name.value,
            "age": int(self.age.value),
            "passport": self.passport.value,
            "from_country": self.from_country.value,
            "to_country": self.to_country.value
        }

        # Send an intermediate message with a button to proceed to the next modal
        await interaction.response.send_message(
            "Basic details received! Click the button below to proceed to additional booking details.",
            view=ProceedToAdditionalDetailsView(self.user_id),
            ephemeral=True
        )

# View with button to trigger the second modal
class ProceedToAdditionalDetailsView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    @discord.ui.button(label="Proceed to Additional Details", style=discord.ButtonStyle.primary)
    async def proceed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AdditionalDetailsModal(self.user_id))

class AdditionalDetailsModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="✈️ Additional Booking Details")
        self.user_id = user_id

        self.category = TextInput(label="Travel Class", placeholder="Business, Economy, First Class", required=True)
        self.price = TextInput(label="Price", placeholder="Enter price", required=True)
        self.departure_date = TextInput(label="Departure Date", placeholder="YYYY-MM-DD", required=True)
        self.arrival_date = TextInput(label="Arrival Date", placeholder="YYYY-MM-DD", required=True)

        self.add_item(self.category)
        self.add_item(self.price)
        self.add_item(self.departure_date)
        self.add_item(self.arrival_date)

    async def on_submit(self, interaction: discord.Interaction):
        # Retrieve data from the first modal
        basic_details = temp_data.get(self.user_id)
        if not basic_details:
            await interaction.response.send_message("No basic details found.", ephemeral=True)
            return

        ticket_id = generate_ticket_id()

        # Save booking to the database
        c.execute(
            '''INSERT INTO bookings (ticket_id, name, age, passport, from_country, to_country, category, price, departure_date, arrival_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                ticket_id,
                basic_details["name"],
                basic_details["age"],
                basic_details["passport"],
                basic_details["from_country"],
                basic_details["to_country"],
                self.category.value,
                int(self.price.value),
                self.departure_date.value,
                self.arrival_date.value
            )
        )
        conn.commit()

        # Remove temporary data
        temp_data.pop(self.user_id, None)

        # Send confirmation embed
        embed = discord.Embed(
            title="🎉 **Flight Ticket Purchase**",
            description="Ticket successfully booked! Here are your details:",
            color=0x00ff00
        )
        embed.add_field(name="🆔 Ticket ID", value=ticket_id, inline=False)
        embed.add_field(name="👤 Passenger Name", value=basic_details["name"], inline=True)
        embed.add_field(name="🌍 From", value=basic_details["from_country"], inline=True)
        embed.add_field(name="📍 To", value=basic_details["to_country"], inline=True)
        embed.add_field(name="💺 Class", value=self.category.value, inline=True)
        embed.add_field(name="💵 Price", value=f"${self.price.value}", inline=True)
        embed.set_footer(text="Thank you for choosing our service! We hope you have a pleasant journey.")
        await interaction.response.send_message(embed=embed)

# Button View for starting the booking process
class PurchaseView(View):
    @discord.ui.button(label="Start Booking", style=discord.ButtonStyle.green, emoji="✈️")
    async def start_booking(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Trigger the first modal form for booking
        await interaction.response.send_modal(BasicDetailsModal(interaction.user.id))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket booking process has been canceled.", ephemeral=True)


# Command to initiate the purchase view
@bot.command()
async def purchase(ctx):
    embed = discord.Embed(
        title="✈️ **Flight Ticket Booking**",
        description="Click **Start Booking** to open the ticket booking form, or **Cancel** to exit.",
        color=0x1e90ff
    )
    embed.set_footer(text="Choose an option below to proceed.")

    view = PurchaseView()
    await ctx.send(embed=embed, view=view)

# Command to look up booking details by ticket ID
@bot.command()
async def lookup(ctx):
    await ctx.send("Enter your ticket ID to look up:")
    ticket_id = (await bot.wait_for(
        'message', check=lambda msg: msg.author == ctx.author)).content
    c.execute("SELECT * FROM bookings WHERE ticket_id = ?", (ticket_id, ))
    booking = c.fetchone()

    if booking:
        embed = discord.Embed(title="Flight Booking Details", color=0x1e90ff)
        embed.add_field(name="Ticket ID", value=booking[0], inline=False)
        embed.add_field(name="Passenger Name", value=booking[1], inline=True)
        embed.add_field(name="Age", value=booking[2], inline=True)
        embed.add_field(name="Passport Number", value=booking[3], inline=True)
        embed.add_field(name="From", value=booking[4], inline=True)
        embed.add_field(name="To", value=booking[5], inline=True)
        embed.add_field(name="Category", value=booking[6], inline=True)
        embed.add_field(name="Price", value=f"${booking[7]}", inline=True)
        embed.add_field(name="Departure Date", value=booking[8], inline=True)
        embed.add_field(name="Arrival Date", value=booking[9], inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("Ticket ID not found.")

@bot.command()
async def cancel(ctx):
    await ctx.send("Enter your ticket ID to cancel:")
    ticket_id = (await bot.wait_for(
        'message', check=lambda msg: msg.author == ctx.author)).content
    c.execute("SELECT * FROM bookings WHERE ticket_id = ?", (ticket_id, ))
    booking = c.fetchone()

    if booking:
        c.execute("DELETE FROM bookings WHERE ticket_id = ?", (ticket_id, ))
        conn.commit()
        await ctx.send(
            "Your ticket has been canceled. Your refund will be processed shortly."
        )
    else:
        await ctx.send("Ticket ID not found.")

@bot.command()
async def inquiry(ctx):
    # Creating an embed for the inquiry options
    embed = discord.Embed(
        title="📋 **Flight Inquiry Options**",
        description="Please select an option by typing the corresponding number:\n\n"
                    "1️⃣ **Flight Arrival** - Check the arrival status of your flight.\n"
                    "2️⃣ **Flight Delay** - Get information on any delays.\n"
                    "3️⃣ **Terminal Info** - Find out which terminal your flight is arriving at.",
        color=0x1e90ff
    )
    embed.set_thumbnail(url="https://example.com/airplane_thumbnail.png")  # Replace with an actual image URL
    embed.set_footer(text="Type the number of your choice below.", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

    try:
        # Wait for user response
        option = (await bot.wait_for('message', check=lambda msg: msg.author == ctx.author, timeout=30)).content

        # Respond based on the user's choice
        if option == "1":
            response_embed = discord.Embed(
                title="✈️ **Flight Arrival Status**",
                description="✅ **The flight is expected to arrive on time.**",
                color=0x00ff00  # Green color for success
            )
        elif option == "2":
            response_embed = discord.Embed(
                title="⏳ **Flight Delay Information**",
                description="⚠️ **There is a slight delay in the arrival due to weather conditions.**",
                color=0xffcc00  # Yellow color for caution
            )
        elif option == "3":
            response_embed = discord.Embed(
                title="🏢 **Terminal Information**",
                description="📍 **The flight will arrive at Terminal 3.**",
                color=0x3498db  # Blue color for information
            )
        else:
            response_embed = discord.Embed(
                title="❌ **Invalid Option**",
                description="😕 **Please select a valid option (1, 2, or 3).**",
                color=0xff0000  # Red color for error
            )

        await ctx.send(embed=response_embed)

    except asyncio.TimeoutError:
        await ctx.send("⏰ **You took too long to respond! Please try the command again.**")

@bot.command()
async def support(ctx):
    # Creating an embed for the support options
    embed = discord.Embed(
        title="🛠️ **Support Options**",
        description="Please select an option by typing the corresponding number:\n\n"
                    "1️⃣ **Luggage Delay** - Report any delays with your luggage.\n"
                    "2️⃣ **Missing Items** - Report any missing items.\n"
                    "3️⃣ **Ticket Postpone** - Get help with postponing your ticket.",
        color=0x1e90ff
    )
    embed.set_thumbnail(url="https://example.com/support_thumbnail.png")  # Replace with an actual image URL
    embed.set_footer(text="Type the number of your choice below.", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

    try:
        # Wait for user response
        option = (await bot.wait_for('message', check=lambda msg: msg.author == ctx.author, timeout=30)).content

        # Respond based on the user's choice
        if option == "1":
            response_embed = discord.Embed(
                title="🧳 **Luggage Delay Report**",
                description="🚨 **Your luggage is delayed but will arrive soon. Thank you for your patience!**",
                color=0xffcc00  # Yellow color for caution
            )
        elif option == "2":
            response_embed = discord.Embed(
                title="🔍 **Missing Items Report**",
                description="📞 **Please report any missing items to our customer support for further assistance.**",
                color=0x3498db  # Blue color for information
            )
        elif option == "3":
            response_embed = discord.Embed(
                title="🗓️ **Ticket Postpone Assistance**",
                description="📅 **You can postpone your ticket by contacting support. Our team will assist you shortly.**",
                color=0x00ff00  # Green color for success
            )
        else:
            response_embed = discord.Embed(
                title="❌ **Invalid Option**",
                description="😕 **Please select a valid option (1, 2, or 3).**",
                color=0xff0000  # Red color for error
            )

        await ctx.send(embed=response_embed)

    except asyncio.TimeoutError:
        await ctx.send("⏰ **You took too long to respond! Please try the command again.**")
@bot.command()
async def show_database(ctx):
    c.execute("SELECT * FROM bookings")
    rows = c.fetchall()

    if rows:
        embeds = []
        current_embed = discord.Embed(
            title="📜 **Flight Bookings Database**",
            description="Here are the current bookings in our database:",
            color=0x1e90ff
        )

        field_count = 0

        for row in rows:
            if field_count + 8 > 25:
                # Add the current embed to the list and start a new one
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="📜 **Flight Bookings Database (Continued)**",
                    color=0x1e90ff
                )
                field_count = 0

            # Add fields for each booking
            current_embed.add_field(name="✈️ **Ticket ID**", value=f"`{row[0]}`", inline=False)
            current_embed.add_field(name="👤 **Passenger Name**", value=f"**{row[1]}**", inline=True)
            current_embed.add_field(name="🌍 **From**", value=f"{row[4]}", inline=True)
            current_embed.add_field(name="📍 **To**", value=f"{row[5]}", inline=True)
            current_embed.add_field(name="💺 **Class**", value=f"{row[6]}", inline=True)
            current_embed.add_field(name="🛫 **Departure**", value=f"{row[8]}", inline=True)
            current_embed.add_field(name="🛬 **Arrival**", value=f"{row[9]}", inline=True)
            current_embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            field_count += 8

        # Append the last embed if it has fields
        if field_count > 0:
            embeds.append(current_embed)

        for embed in embeds:
            await ctx.send(embed=embed)
    else:
        await ctx.send("📭 No bookings in the database.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🤖 **Flight Booking Bot Commands**",
        description=
        "Here is a list of available commands for the Flight Booking Bot. Use these to manage bookings, inquire, and get support!",
        color=0x3498db)

    embed.add_field(
        name="🎫 **!purchase**",
        value=
        "Book a new flight. The bot will guide you through entering details like destination, category, and price.",
        inline=False)
    embed.add_field(
        name="🔍 **!lookup**",
        value=
        "Look up an existing booking by entering your Ticket ID to view all details about your flight.",
        inline=False)
    embed.add_field(
        name="❌ **!cancel**",
        value=
        "Cancel a booking by providing your Ticket ID. Confirmation will be requested before final cancellation.",
        inline=False)
    embed.add_field(
        name="ℹ️ **!inquiry**",
        value=
        "Get flight information such as arrival status, delays, and terminal details.",
        inline=False)
    embed.add_field(
        name="🛠️ **!support**",
        value=
        "Contact support for issues like luggage delay, missing items, or ticket postponement options.",
        inline=False)
    embed.add_field(
        name="📄 **!show_database**",
        value=
        "Display all current bookings in the database. Useful for admins to view existing reservations.",
        inline=False)
    embed.add_field(
        name="💡 **!help**",
        value=
        "Displays this help message, listing all available commands and their descriptions.",
        inline=False)

    embed.set_footer(
        text=
        "Use the appropriate command prefix before each command (e.g., !purchase)."
    )

    await ctx.send(embed=embed)

@bot.event
async def on_close():
    conn.close()
# Run the bot
bot.run(
    'TOKEN GOES HERE')
