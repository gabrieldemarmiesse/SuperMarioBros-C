#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>

#include "../Emulation/Controller.hpp"

#include "Movie.hpp"

/**
 * The button for each character position of a controller field ("RLDUTSBA").
 */
static const ControllerButton buttonOrder[8] = {
    BUTTON_RIGHT,
    BUTTON_LEFT,
    BUTTON_DOWN,
    BUTTON_UP,
    BUTTON_START,
    BUTTON_SELECT,
    BUTTON_B,
    BUTTON_A
};

bool loadMovie(const std::string& fileName, std::vector<MovieFrame>& frames)
{
    std::ifstream file(fileName);
    if (!file)
    {
        std::cout << "Failed to open the movie file \"" << fileName << "\"." << std::endl;
        return false;
    }

    std::string line;
    int lineNumber = 0;
    while (std::getline(file, line))
    {
        lineNumber++;

        // Handle files with Windows line endings
        //
        if (!line.empty() && line.back() == '\r')
        {
            line.pop_back();
        }

        // Only lines starting with '|' contain input. Everything else (such as FM2 header lines) is ignored.
        //
        size_t start = line.find_first_not_of(" \t");
        if (start == std::string::npos || line[start] != '|')
        {
            continue;
        }

        std::vector<std::string> fields;
        std::stringstream lineStream(line.substr(start + 1));
        std::string field;
        while (std::getline(lineStream, field, '|'))
        {
            fields.push_back(field);
        }

        MovieFrame frame = {};

        // Commands field
        //
        const std::string commands = fields.empty() ? "" : fields[0];
        if (commands.find_first_not_of("0123456789") != std::string::npos)
        {
            std::cout << fileName << ":" << lineNumber << ": invalid commands field \"" << commands
                      << "\", expected a number." << std::endl;
            return false;
        }
        frame.reset = (std::atoi(commands.c_str()) & 0x3) != 0;

        // Controller fields
        //
        for (size_t controller = 0; controller < 2 && controller + 1 < fields.size(); controller++)
        {
            const std::string& buttons = fields[controller + 1];
            if (!buttons.empty() && buttons.size() != 8)
            {
                std::cout << fileName << ":" << lineNumber << ": invalid input \"" << buttons << "\" for controller "
                          << (controller + 1) << ", expected 8 characters in RLDUTSBA order." << std::endl;
                return false;
            }

            for (size_t i = 0; i < buttons.size(); i++)
            {
                frame.buttons[controller][buttonOrder[i]] = (buttons[i] != '.' && buttons[i] != ' ');
            }
        }

        frames.push_back(frame);
    }

    return true;
}
