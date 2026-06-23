# of-light-and-dark
a scrolling platformer for the noodles (everything is for the noodles). Demo is fully working. 

## Usage

- **Itch**

    This project can be accessed on [itch.io](https://uselesslyuseful.itch.io/of-light-and-dark). There is currently no mobile support. 

- **Cloning**

   This game uses the pygame module. Use the package manager [pip](https://pip.pypa.io/en/stable/) to install pygame.

   ```bash
   pip install pygame
   ```

## Code

- **Structure**

    All code for the game is in main.py.

- **AI Usage & Other borrowed code**

    No AI was used (...theoretically) during the duration of this project. However, player & enemy (generation, collisions in the Game class, movement & accompanying physics) mechanics were direct copy pastes from a former platformer I've made, and I cannot for the life of me remember if I used AI to generate it. 

## Features

- **Movement**
   
   Arrow keys are used to move player and to jump. Space is used to turn flashlight on/off (see more in Flashlight and Phantom Blocks) 

- **Obstacles**
  
  There are four types of obstacles (the game treats staircases as its own type for the sake of generation, but it's just a collection of blocks). The world generates these infinitely in chunks, and new chunks only generate once it will be visible on screen. 

    - **Blocks**
    
    This is the base of the game, functionally: 1x1 blocks are shoved together (or diagonally for staircases) to make the majority of the platforms. Spikes can spawn on blocks that are a part of a flat platform, and the length of platforms is randomized to be between 1 and 10. 

    - **Spikes**
    
    Spike generate in red, and touching one kills the player. They can only generate on flat platforms, not staircases. They're also hard coded to not generate with only one block of space in between, or on the beginning of a platform.

    - **Enemies**

    Enemies are generated along with the platform (5-9 blocks) they loop back and forth on. Touching one kills the player, and they're only visible outside of the light. Once you pass one, it disappears forever.

    - **Phantom Blocks**

    These are denoted using dashed lines, and behave generally similar to normal blocks. However, they're only tangible (can be collided with) when the flashlight is turned off. Spikes and enemies can't generate on them.

- **Flashlight**

    Also known as the only mechanic I could think of to make the game unique oops- The flashlight is functionally a circle of the darkness that doesn't get drawn. In the circle, everything is visible, when it's turned off (space) only the stuff directly next to the player is visible. The flashlight uses 1% battery every second, and charges at 0.5% battery every second (charges when turned off). 

## Support

Gmail: sleep.cats.books@gmail.com
