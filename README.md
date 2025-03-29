# Packet Radio Terminal Project
Bringing Mainframe Magic to 1200-Baud AX.25

Imagine a terminal screen--cursor blinking, forms ready to fill--not some clunky teletype spitting out endless text. That's my goal: a slick, interactive mainframe vibe built for amateur packet radio, squeezed into 2-meter AX.25 at 1200 baud. Old-school packet setups are stuck in the 80s: slow scrolls, no way to jump around. I'm crafting something you can actually use, even on a tiny trickle of bandwidth.

## The Bandwidth Squeeze
Take a classic terminal like the VT-100. It redraws a whole 80x24 screen--1920 characters--every time. At 1200 baud (120 characters per second), that's 16 seconds for one refresh. Add a few more users, and you're waiting forever. Packet radio can't keep up with that noise, so I flipped the script.

## Forms: The Clever Trick
My server, humming on a Raspberry Pi 4, dishes out 'forms'--simple text templates (TXT files) with spots for data. At startup, clients grab these forms once--a couple-minute download--and then they're set. From there, only the data zips back and forth, not entire screens. That makes 1200 baud plenty. A dozen hams on the network? No sweat. A regular mainframe would choke trying this with even one user.

## How It Stays in Sync
Every 60 seconds, the server blasts out an MD5 hash--a quick "version number" of its form collection. Clients listen, check it against their own stash (form names and hashes), and if something's off, one pipes up with, "Hey, send me the updates!" and its list. The server spots the differences and sends only what's new or changed. Everyone else listening snags the same fixes--no repeats, no wasted airtime. Miss a packet because of static? The next broadcast gets you back on track.

## The Nuts and Bolts
Data lives in CSVs on the server--one file per form for submissions, plus a few key files tying it all together like a lightweight database. No bloated MySQL here; it's simple enough to run on a Pi with a battery pack. Both server and client lean on Direwolf software, a DigiRig Mobile, and a Radio Shack HTX-242 radio--a tough, portable kit perfect for the field.

## The Lineup
- server.py: The brains. Creates, edits, and deletes forms with a handy Forms Management System. Saves submissions and can ping data back to clients.
- terminal_client.py: The face. Gives you a terminal UI you can navigate--not just a scrolling mess--for typing in and checking data.
- client_install.sh: The setup guy. Gets client machines ready with directories, permissions, and the bits they need to run.

## Why It's a Big Deal
This isn't just a retro geek-out--it's useful. Picture a dozen hams logging emergencies, requesting gear, or swapping updates over packet radio, all from a Pi and a rugged laptop like my Panasonic CF-29 Mk3. It's a homebrew mashup of old-school computing and ham radio grit, showing you can do big things with next to no bandwidth.
