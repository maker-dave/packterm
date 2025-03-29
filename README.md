*Packet Radio Terminal Project

Bringing Mainframe Magic to 1200-Baud AX.25

Picture a terminal screen—cursor blinking, forms waiting—not a teletype churning out endless text. That’s my mission: a mainframe-terminal experience crafted for amateur packet radio, squeezed into 2-meter AX.25 at 1200 baud. Traditional packet interfaces feel stuck in the 80s: linear scrolls, no navigation. I’m building a system that’s interactive, even on a trickle of bandwidth.

The Bandwidth Bottleneck
Classic terminals like the VT-100 rely on constant screen refreshes—1920 characters for an 80x24 display. At 1200 baud (120 chars/sec), that’s 16 seconds per redraw for one client. Scale to more users, and it’s glacial. Packet radio can’t handle that chatter, so I turned the problem inside out.

Forms: The Secret Sauce
My server—running on a Raspberry Pi 4—creates ‘forms’: lightweight screen templates (TXT files) with fields for data entry or display. At startup, clients sync these forms once, taking a few minutes instead of pinging the server endlessly. After that, only the data moves—no full screens—making 1200 baud work. A dozen clients? Easy. A traditional mainframe couldn’t manage even one this way.

How It Syncs
The server broadcasts an MD5 hash of its forms index every 60 seconds—a “version check.” Clients listen, compare it to their own index (form names + hashes), and if it’s off, one says, “Send updates!” with its index. The server diffs them, then broadcasts missing or updated forms. Everyone listening grabs what they need—no duplicate requests, just smart airtime. Missed a packet due to QRM? The next MD5 ping catches you up.

Guts of the System
Data sits in CSVs on the server—one per form for submissions, plus key files linking them like a mini relational database. No MySQL heft here; it’s lean enough for a Pi on a battery bank. Both server and client use Direwolf, a DigiRig Mobile, and a Radio Shack HTX-242 transceiver—a portable, rugged setup for field ops.

The Pieces
server.py: The brain. Builds, edits, and deletes forms via a Forms Management System. Stores submissions and can push data back to clients.
terminal_client.py: The face. Delivers a navigable terminal UI, not a teletype scroll, for entering and viewing data.
client_install.sh: The setup crew. Preps directories, permissions, and dependencies on client machines.
Why It Matters
This isn’t just nostalgia—it’s practical. A dozen hams could log incidents, request supplies, or share status reports over packet radio, all from a Pi and a ToughBook like my Panasonic CF-29 Mk3. It’s a DIY bridge between retro computing and ham radio grit, proving big ideas thrive on small bandwidth.
