# IslandBot by Djarrah
*A simple Discord bot in Python I made for the Symvasi RPG.*

It implements 2 user movement types(affected by user timers) + 1 forced admin movement type commands thanks to json support.
A 3-hours routine taks sends a backup of the data.json to a set backup channel.

**This project will not have future versions unless i decide to re-use it for another RPGs. You can use it as a baseline for your own bot.**

#### Other commands include:
- !look to show a jpeg image in the media/look folder with the same name as the current channel
- !sendfile to send a general file
- !say to speak through the bot
- !roll to roll a number of d6s and show their single results(not sum)
- other commands to disable movement from/to channels, hide channels, add channels to a movement network, empty a movement network while saving a bk state, resuming that state
- a setting-specific command to assign an hotel room(channel) to a single player(Member)

## How to set up the bot for your use:
1. Edit the TOKEN variable in the code if you are not using Heroku: use a simple string or better, an .env file(use dotenv to import it).
    - If you are using Heroku, simply paste the TOKEN as a local variable of your app.
2. Edit the backup channel id in the backup routine or delete it entirely.
3. Customize the movemement commands and/or the movemement support commands
4. Customize your data.json with movement networks.

## How to customize the movement types and networks in data.json :
- The default movement(!walk) uses the "available destinations" dictionary as a bigger network.
    - First it checks if a key matches the channel's group. If positive, the value list becomes a network. (It usually contains all the channels in the group, useful in places where multiple locations are connected to each other, such as an hotel)
        - Certain channel groups may follow special rules, such as the Private Quarters, which i used to let each player only access their bedroom.
    - If the group is an exception, a key matching the channel's name is searched, and its value list used as a network. (This is useful with locations wich connects only to certain other locations)
- Certain types of movements(such as !bus) have their own key, with their list value as a network. (Useful if this movement can only reach certain locations, as the bus can only use main roads)
- Other Key: List pairs are used to hide locations or to lock them, or to serve as a backup for certain networks.
- Key: Dict pairs are used to handle cooldowns and special features such as room owners.
