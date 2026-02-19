#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif // MACRO

typedef enum
{
    STATE_RED,
    STATE_GREEN,
    STATE_YELLOW,

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
        system("clear || cls");
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
            printf("unkwn state!\n");
            return 1;
        }
    }
    return 0;
}