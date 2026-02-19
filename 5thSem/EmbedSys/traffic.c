#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

typedef enum
{
    STATE_RED,
    STATE_GREEN,
    STATE_YELLOW
} TrafficSys;

void delay_ms(int ms)
{
#ifdef _WIN32
    Sleep(ms);
#else
    usleep(ms * 1000);
#endif
}

int main()
{
    TrafficSys currentState = STATE_RED;

    int green_light = 5000;
    int yellow_light = 1000;
    int red_light = 8000;

    while (1)
    {

        switch (currentState)
        {
        case STATE_RED:
            printf("Traffic Light: Red\n");
            delay_ms(red_light);
            currentState = STATE_YELLOW;
            break;

        case STATE_YELLOW:
            printf("Traffic Light: Yellow\n");
            delay_ms(yellow_light);
            currentState = STATE_GREEN;
            break;

        case STATE_GREEN:
            printf("Traffic Light: Green\n");
            delay_ms(green_light);
            currentState = STATE_RED;
            break;

        default:
            printf("unknown state!\n");
            return 1;
        }
    }
    return 0;
}

// #include <stdio.h>
// #include <stdlib.h>
// #include <time.h>
// #include <conio.h> // for _kbhit() and _getch()

// // Enum for traffic light states
// enum Light
// {
//     GREEN,
//     YELLOW,
//     RED
// };

// // Function to wait for some seconds
// void wait(int seconds)
// {
//     time_t start = time(NULL);
//     while (time(NULL) - start < seconds)
//     {
//         // just waiting
//     }
// }

// // Function to simulate traffic light controller
// void trafficLightController(int interval)
// {
//     enum Light current = GREEN;

//     printf("\nPress any key to exit the simulation...\n");
//     while (1)
//     {
//         // clear the screen
//         // system("cls");

//         // print current light
//         switch (current)
//         {
//         case GREEN:
//             printf("Light: GREEN\n");
//             current = YELLOW;
//             break;
//         case YELLOW:
//             printf("Light: YELLOW\n");
//             current = RED;
//             break;
//         case RED:
//             printf("Light: RED\n");
//             current = GREEN;
//             break;
//         }

//         // wait for interval
//         wait(interval);

//         // if user pressed a key, exit
//         if (_kbhit())
//         {
//             _getch(); // read the key
//             system("cls");
//             printf("Simulation stopped by user.\n");
//             break;
//         }
//     }
// }

// int main()
// {
//     int interval = 2; // seconds between lights
//     trafficLightController(interval);
//     return 0;
// }