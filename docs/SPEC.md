#### Let's write a technical task for LifeU

###  Task Valuer AI

Input: Text from user, which describes what he have done.

Output: json, only json in this format

{
Value: int, 0-100, how much valuable and hard was this task, for example 1 for taking trash out, 10 for a run, 100 for completing hard a project

Awareness: 0-100 percentage, how much awareness was needed to complete this task

Curiosity: 0-100 percentage, how much curiosity was needed to complete this task

Willpower: 0-100 percentage, how much Willpower was needed to complete this task

Compassion: 0-100 percentage, how much Compassion was needed to complete this task

Discipline: 0-100 percentage, how much Discipline was needed to complete this task
}

### Reward Classifier AI

Input: Text. Can be from user, if the user wants some kind of reward hiding in chests. Or it can be secret message text from user's friend, for example: "I promise a lunch by me if you open this chest"

Output: json, only json format
{
Value: 0-100, percentage. Value of this reward, 1 for a motivational quote, 10 for a lunch at favorite restaurant or a png art piece, 85 for a secret lunch from a friend (more valueable since it is a secret, has anticipation since I can't guess it, and also my friend treats me, it's amazing) Secret message are always higher, even we can say that they are always above 50, even if it's just a motivational text

Class: [] array of strings. 1-3 string choosen from this list {Nurturing, Determination, Adaptability, Presence, Transformation, Reflection, Serenity, Inspiration, Vitality, Freedom}. There can be only 1-3 classes assigned to one reward. For which word this reward more relates
}


###  Task Valuer AI Response Wrapper

takes the ai response and returns what the user earned completing the task.
average_virtue = (Awareness + Curiosity + Willpower + Compassion + Discipline) / 5

 - 🌌 Space Fragment: average_virtue * Awareness * value * constants.VirtueTuner
 - 🌬️ Air Fragment: average_virtue * Curiosity * value * constants.VirtueTuner
 - 🔥 Fire Fragment: average_virtue * Willpower * value * constants.VirtueTuner
 - 💧 Water Fragment: average_virtue * Compassion * value * constants.VirtueTuner
 - 🌍 Earth Fragment: average_virtue * Discipline * value * constants.VirtueTuner

### Reward Classifier AI Response Wrapper

Takes the ai response and returns a Receptacle which contains this reward.
The Virtue of the Receptacle is randomly chosen from the class provided by AI

### Task repository

A repository which retrieves and saves all the writes tasks into a database with date and time. So we have a history of done tasks. Also it has some methods for statistics

### Collectables repository

A repository that stores all the current collectables count in a database. 
There are 16 elemental types:
- | 🌌 Space  |
- | 🌬️ Air   |
- | 🔥 Fire   |
- | 💧 Water  |
- | 🌍 Earth  |
- | ✨ Harmony |
- | Growth 🌱   |
- | Forge ⚒️    |
- | Dust 🌫️    |
- | Mountain ⛰️ |
- | Steam ☁️    |
- | Mist 🌁     |
- | Ocean 🌊    |
- | Lightning ⚡ |
- | Sun ☀️      |
- | Wind 🌪️    |
And 6 rarity types:
- | Fragment |
- | Shard    |
- | Crystal  |
- | Essence  |
- | Soul     |
- | Core     |
So by combinations there are 96 types of collectables
For example Space fragment, lighting crystal, Sun core
### Collectables merger

3 collectables of same type (except core) can be merged to become more rare type of it
Fragment -> Shard -> Crystal -> Essence -> Soul -> Core

Adding all five base elementals with same rarity creates harmony collectables with same rarity. For example
🌌 Space  Fragment+ 🌬️ Air  Fragment+ 🔥 Fire  Fragment+ 💧 Water  Fragment+ 🌍 Earth Fragment = 5+ ✨ Harmony Fragments
Resulted number of Harmony collectables depend of randomness like this. First on the screen pops up 5 harmony ones, and then the animation of build up, and adds extra harmony collectable with 50% chance, if it got extra then it continues the build up animation and tries again. So in theory it can go on getting extra infinitely, but in practice of course it's highly unlikely. It only stops when extra didn't drop

Harmony can be used to merge two base element collectables. All of them with same rarity of course. Using this mapping table.

| Combination   | Result      |
| ------------- | ----------- |
| Earth + Water | Growth 🌱   |
| Earth + Fire  | Forge ⚒️    |
| Earth + Air   | Dust 🌫️    |
| Earth + Space | Mountain ⛰️ |
| Water + Fire  | Steam ☁️    |
| Water + Air   | Mist 🌁     |
| Water + Space | Ocean 🌊    |
| Fire + Air    | Lightning ⚡ |
| Fire + Space  | Sun ☀️      |
| Air + Space   | Wind 🌪️    |
### Receptacle Repository
It contains all opened and not opened Receptacles. 
The are 10 types of virtues:
- | Nurturing      |
- | Determination  |
- | Adaptability   |
- | Presence       |
- | Transformation |
- | Reflection     |
- | Serenity       |
- | Inspiration    |
- | Vitality       |
- | Freedom        |
And 6 rarity types:
- | Pouch   |
- | Sack    |
- | Chest   |
- | Safe    |
- | Vault   |
- | Sanctum |
So by combinations, there are 60 types of Receptacles

Every Receptacles contains random number of coins.
Pounches and Sackes are genereted Receptacles. Pounches contains some random motivational quote or some interesting fact. Sackes contains some discovery, it may contain new music or some art piece from artstation or deviantart.

Higher receptacles are collected according to this mechanics:
User or his friend writes a text, AI will evaluate it.
Virtue is assigned by AI but rarity is calculated by repository. 
Everytime collection of Receptacles changes,  (added, updated or removed) recalculates the rarities. It first takes all the Receptacles (except generated ones), even opened ones and orders them by value and assignees rarities so that count of them will have ratio of Chest:Safe:Vault:Sanctum = 27:9:3:1. Assigtment onto already opened receptacles will not apply. After it opened it never changes but attends to rarity assignee calculation. 

### Treasure Repository
There will be 3 treasures everytime.
When treasure is generated, it contains 5-10 random not opened Receptacles from the repository (not generated ones), desirably with random rarities. Every treasure has it's own price according to what it owns. On every buy of treasure it may drop any Receptacle in it, or random genereted Pounch or a Sack. Drop chances looks like this

| Rarity    | Receptacle | Chance     | Pity |
| --------- | ---------- | ---------- | ---- |
| Common    | Pouch      | 100%       | N/A  |
| Uncommon  | Sack       | 1/3 = 33%  | N/A  |
| Rare      | Chest      | 1/9 = 11%  | N/A  |
| Epic      | Safe       | 1/27=3.7%  | N/A  |
| Legendary | Vault      | 1/81=1.2%  | 27   |
| Mythic    | Sanctum    | 1/243=0.4% | 81   |
Pity is if that many times the user bought the treasure but that rarity didn't drop then it 100% drops.  The treasure disappears if the user collected all the items or he chooses lose the treasure option which is available only once a day. When it disappears new treasure will take place


### Miscellaneous details

- Groq will be used for AI, since it's fast to start with and also free.
- Backend python Django with tests and swagger
- Backend is coded SoC with db, so it can be replaced easily later. Currently it's just a firebase, because it's free for protypes and it's always online available. Later we can change to real DB. 
- Frontend in react three.js. Try to design like effective only one tab app. There shouldn't be more pages, just a one page with all the logic and beauty contained
- Everything coded with SOLID principle, readable, manageable and testable.