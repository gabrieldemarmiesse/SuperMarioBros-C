/**
 * @file
 * @brief defines utilities for playing back pre-recorded controller input (movies).
 */
#ifndef MOVIE_HPP
#define MOVIE_HPP

#include <string>
#include <vector>

/**
 * Controller input for a single frame of a movie.
 */
struct MovieFrame
{
    bool reset;         /**< Whether the game is reset before this frame runs. */
    bool buttons[2][8]; /**< Button states for controllers 1 and 2, indexed by ControllerButton. */
};

/**
 * Load a movie from an FCEUX-style (.fm2) text file.
 *
 * Every line that starts with '|' is the input for one frame, in the format "|commands|controller1|controller2|".
 * Each controller field is either empty or 8 characters in "RLDUTSBA" order (Right, Left, Down, Up, sTart, Select,
 * B, A), where '.' or ' ' means released and any other character means pressed. The commands field is a number
 * where bit 0 (soft reset) or bit 1 (hard reset) resets the game. All other lines are ignored.
 *
 * @param fileName the movie file to load.
 * @param frames receives the input for each frame.
 * @return true if the movie was loaded successfully.
 */
bool loadMovie(const std::string& fileName, std::vector<MovieFrame>& frames);

#endif // MOVIE_HPP
