#include <chrono>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include <SDL2/SDL.h>

#include "Emulation/Controller.hpp"
#include "SMB/SMBConstants.hpp"
#include "SMB/SMBEngine.hpp"
#include "Util/Movie.hpp"
#include "Util/Video.hpp"

#include "Configuration.hpp"
#include "Constants.hpp"

uint8_t* romImage;
static SDL_Window* window;
static SDL_Renderer* renderer;
static SDL_Texture* texture;
static SDL_Texture* scanlineTexture;
static SMBEngine* smbEngine = nullptr;
static uint32_t renderBuffer[RENDER_WIDTH * RENDER_HEIGHT];

/**
 * Load the Super Mario Bros. ROM image.
 */
static bool loadRomImage()
{
    FILE* file = fopen(Configuration::getRomFileName().c_str(), "r");
    if (file == NULL)
    {
        std::cout << "Failed to open the file \"" << Configuration::getRomFileName() << "\". Exiting.\n";
        return false;
    }

    // Find the size of the file
    fseek(file, 0L, SEEK_END);
    size_t fileSize = ftell(file);
    fseek(file, 0L, SEEK_SET);

    // Read the entire file into a buffer
    romImage = new uint8_t[fileSize];
    fread(romImage, sizeof(uint8_t), fileSize, file);
    fclose(file);

    return true;
}

/**
 * SDL Audio callback function.
 */
static void audioCallback(void* userdata, uint8_t* buffer, int len)
{
    if (smbEngine != nullptr)
    {
        smbEngine->audioCallback(buffer, len);
    }
}

/**
 * Initialize libraries for use.
 *
 * @param headless if true, only initialize what is needed to run the game, without video or audio.
 */
static bool initialize(bool headless)
{
    // Load the configuration
    //
    Configuration::initialize(CONFIG_FILE_NAME);

    // Load the SMB ROM image
    if (!loadRomImage())
    {
        return false;
    }

    if (headless)
    {
        return true;
    }

    // Initialize SDL
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) < 0)
    {
        std::cout << "SDL_Init() failed during initialize(): " << SDL_GetError() << std::endl;
        return false;
    }

    // Create the window
    window = SDL_CreateWindow(APP_TITLE,
                              SDL_WINDOWPOS_UNDEFINED,
                              SDL_WINDOWPOS_UNDEFINED,
                              RENDER_WIDTH * Configuration::getRenderScale(),
                              RENDER_HEIGHT * Configuration::getRenderScale(),
                              0);
    if (window == nullptr)
    {
        std::cout << "SDL_CreateWindow() failed during initialize(): " << SDL_GetError() << std::endl;
        return false;
    }

    // Setup the renderer and texture buffer
    renderer = SDL_CreateRenderer(window, -1, (Configuration::getVsyncEnabled() ? SDL_RENDERER_PRESENTVSYNC : 0) | SDL_RENDERER_ACCELERATED);
    if (renderer == nullptr)
    {
        std::cout << "SDL_CreateRenderer() failed during initialize(): " << SDL_GetError() << std::endl;
        return false;
    }

    if (SDL_RenderSetLogicalSize(renderer, RENDER_WIDTH, RENDER_HEIGHT) < 0)
    {
        std::cout << "SDL_RenderSetLogicalSize() failed during initialize(): " << SDL_GetError() << std::endl;
        return false;
    }

    texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, RENDER_WIDTH, RENDER_HEIGHT);
    if (texture == nullptr)
    {
        std::cout << "SDL_CreateTexture() failed during initialize(): " << SDL_GetError() << std::endl;
        return false;
    }

    if (Configuration::getScanlinesEnabled())
    {
        scanlineTexture = generateScanlineTexture(renderer);
    }

    // Set up custom palette, if configured
    //
    if (!Configuration::getPaletteFileName().empty())
    {
        const uint32_t* palette = loadPalette(Configuration::getPaletteFileName());
        if (palette)
        {
            paletteRGB = palette;
        }
    }

    if (Configuration::getAudioEnabled())
    {
        // Initialize audio
        SDL_AudioSpec desiredSpec;
        desiredSpec.freq = Configuration::getAudioFrequency();
        desiredSpec.format = AUDIO_S8;
        desiredSpec.channels = 1;
        desiredSpec.samples = 2048;
        desiredSpec.callback = audioCallback;
        desiredSpec.userdata = NULL;

        SDL_AudioSpec obtainedSpec;
        SDL_OpenAudio(&desiredSpec, &obtainedSpec);

        // Start playing audio
        SDL_PauseAudio(0);
    }

    return true;
}

/**
 * Shutdown libraries for exit.
 */
static void shutdown()
{
    SDL_CloseAudio();

    SDL_DestroyTexture(scanlineTexture);
    SDL_DestroyTexture(texture);
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);

    SDL_Quit();
}

/**
 * Set up the controllers (and reset the game, if needed) for the next frame of a movie.
 */
static void applyMovieFrame(SMBEngine& engine, const MovieFrame& input)
{
    if (input.reset)
    {
        engine.reset();
    }
    for (int button = 0; button < 8; button++)
    {
        engine.getController1().setButtonState((ControllerButton)button, input.buttons[0][button]);
        engine.getController2().setButtonState((ControllerButton)button, input.buttons[1][button]);
    }
}

/**
 * Play a movie as fast as possible without video or audio, then print the final state of the game.
 */
static void runHeadless(const std::vector<MovieFrame>& movie)
{
    SMBEngine engine(romImage);
    engine.reset();

    auto startTime = std::chrono::steady_clock::now();
    for (const MovieFrame& input : movie)
    {
        applyMovieFrame(engine, input);
        engine.update(false);
    }
    auto elapsedTime = std::chrono::steady_clock::now() - startTime;

    static const char* operModeNames[] = {"title", "game", "victory", "game over"};
    uint8_t operMode = engine.readRAM(OperMode);
    int gameTimer = engine.readRAM(GameTimerDisplay) * 100 +
                    engine.readRAM(GameTimerDisplay + 1) * 10 +
                    engine.readRAM(GameTimerDisplay + 2);

    std::cout << "frames: " << movie.size() << "\n"
              << "elapsed_ms: " << std::chrono::duration_cast<std::chrono::milliseconds>(elapsedTime).count() << "\n"
              << "mode: " << (operMode <= GameOverModeValue ? operModeNames[operMode] : "unknown") << "\n"
              << "world: " << engine.readRAM(WorldNumber) + 1 << "-" << engine.readRAM(LevelNumber) + 1 << "\n"
              << "player_x: " << engine.readRAM(Player_PageLoc) * 256 + engine.readRAM(Player_X_Position) << "\n"
              << "player_y: " << (int)engine.readRAM(Player_Y_Position) << "\n"
              << "player_x_speed: " << (int)(int8_t)engine.readRAM(Player_X_Speed) << "\n"
              << "timer: " << gameTimer << "\n"
              << "lives: " << engine.readRAM(NumberofLives) + 1 << std::endl;
}

/**
 * Run the game until the user quits.
 *
 * @param movie if not null, the controller input for each frame is taken from this movie until it ends,
 * after which control returns to the keyboard.
 */
static void mainLoop(const std::vector<MovieFrame>* movie)
{
    SMBEngine engine(romImage);
    smbEngine = &engine;
    engine.reset();

    bool running = true;
    int progStartTime = SDL_GetTicks();
    int frame = 0;
    size_t movieFrame = 0;
    while (running)
    {
        SDL_Event event;
        while (SDL_PollEvent(&event))
        {
            switch (event.type)
            {
            case SDL_QUIT:
                running = false;
                break;
            case SDL_WINDOWEVENT:
                switch (event.window.event)
                {
                case SDL_WINDOWEVENT_CLOSE:
                    running = false;
                    break;
                }
                break;

            default:
                break;
            }
        }

        const Uint8* keys = SDL_GetKeyboardState(NULL);
        Controller& controller1 = engine.getController1();
        Controller& controller2 = engine.getController2();

        if (movie != nullptr && movieFrame == movie->size())
        {
            std::cout << "Movie finished after " << movieFrame << " frames. Keyboard control restored." << std::endl;
            movie = nullptr;

            // Only the movie drives controller 2, so release its buttons
            for (int button = 0; button < 8; button++)
            {
                controller2.setButtonState((ControllerButton)button, false);
            }
        }

        if (movie != nullptr)
        {
            // Movie playback: the input for this frame comes from the movie
            applyMovieFrame(engine, (*movie)[movieFrame++]);
        }
        else
        {
            controller1.setButtonState(BUTTON_A, keys[SDL_SCANCODE_X]);
            controller1.setButtonState(BUTTON_B, keys[SDL_SCANCODE_Z]);
            controller1.setButtonState(BUTTON_SELECT, keys[SDL_SCANCODE_BACKSPACE]);
            controller1.setButtonState(BUTTON_START, keys[SDL_SCANCODE_RETURN]);
            controller1.setButtonState(BUTTON_UP, keys[SDL_SCANCODE_UP]);
            controller1.setButtonState(BUTTON_DOWN, keys[SDL_SCANCODE_DOWN]);
            controller1.setButtonState(BUTTON_LEFT, keys[SDL_SCANCODE_LEFT]);
            controller1.setButtonState(BUTTON_RIGHT, keys[SDL_SCANCODE_RIGHT]);

            if (keys[SDL_SCANCODE_R])
            {
                // Reset
                engine.reset();
            }
        }
        if (keys[SDL_SCANCODE_ESCAPE])
        {
            // quit
            running = false;
            break;
        }
        if (keys[SDL_SCANCODE_F])
        {
            SDL_SetWindowFullscreen(window, SDL_WINDOW_FULLSCREEN_DESKTOP);
        }

        engine.update();
        engine.render(renderBuffer);

        SDL_UpdateTexture(texture, NULL, renderBuffer, sizeof(uint32_t) * RENDER_WIDTH);

        SDL_RenderClear(renderer);

        // Render the screen
        SDL_RenderSetLogicalSize(renderer, RENDER_WIDTH, RENDER_HEIGHT);
        SDL_RenderCopy(renderer, texture, NULL, NULL);

        // Render scanlines
        //
        if (Configuration::getScanlinesEnabled())
        {
            SDL_RenderSetLogicalSize(renderer, RENDER_WIDTH * 3, RENDER_HEIGHT * 3);
            SDL_RenderCopy(renderer, scanlineTexture, NULL, NULL);
        }

        SDL_RenderPresent(renderer);

        /**
         * Ensure that the framerate stays as close to the desired FPS as possible. If the frame was rendered faster, then delay. 
         * If the frame was slower, reset time so that the game doesn't try to "catch up", going super-speed.
         */
        int now = SDL_GetTicks();
        int delay = progStartTime + int(double(frame) * double(MS_PER_SEC) / double(Configuration::getFrameRate())) - now;
        if(delay > 0) 
        {
            SDL_Delay(delay);
        }
        else 
        {
            frame = 0;
            progStartTime = now;
        }
        frame++;
    }
}

int main(int argc, char** argv)
{
    // Parse the command line
    //
    bool headless = false;
    const char* movieFileName = nullptr;
    for (int i = 1; i < argc; i++)
    {
        if (std::string(argv[i]) == "--headless")
        {
            headless = true;
        }
        else if (movieFileName == nullptr)
        {
            movieFileName = argv[i];
        }
        else
        {
            std::cout << "Usage: " << argv[0] << " [--headless] [movie file]\n";
            return -1;
        }
    }
    if (headless && movieFileName == nullptr)
    {
        std::cout << "Headless mode requires a movie file. Usage: " << argv[0] << " --headless <movie file>\n";
        return -1;
    }

    // An optional movie file provides the controller input for each frame
    //
    std::vector<MovieFrame> movie;
    if (movieFileName != nullptr)
    {
        if (!loadMovie(movieFileName, movie))
        {
            std::cout << "Failed to load the movie file. The program will now exit.\n";
            return -1;
        }
        std::cout << "Loaded movie \"" << movieFileName << "\" with " << movie.size() << " frames." << std::endl;
    }

    if (!initialize(headless))
    {
        std::cout << "Failed to initialize. Please check previous error messages for more information. The program will now exit.\n";
        return -1;
    }

    if (headless)
    {
        runHeadless(movie);
        return 0;
    }

    mainLoop(movieFileName != nullptr ? &movie : nullptr);

    shutdown();

    return 0;
}
