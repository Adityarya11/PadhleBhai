#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <semaphore.h>
#include <unistd.h>

#define BUFFER_SIZE 5

int buffer[BUFFER_SIZE];
int top = -1;   // stack-like buffer

sem_t empty;    // counts empty slots
sem_t full;     // counts filled slots
pthread_mutex_t mutex;

void *producer(void *arg) {
    int item = *(int *)arg;

    sem_wait(&empty);
    pthread_mutex_lock(&mutex);

    top++;
    buffer[top] = item;
    printf("Producer produces the item %d\n", item);

    pthread_mutex_unlock(&mutex);
    sem_post(&full);

    return NULL;
}

void *consumer(void *arg) {
    sem_wait(&full);
    pthread_mutex_lock(&mutex);

    if (top >= 0) {
        int item = buffer[top];
        printf("Consumer consumes item %d\n", item);
        top--;
    } else {
        printf("Buffer is empty!!\n");
    }

    pthread_mutex_unlock(&mutex);
    sem_post(&empty);

    return NULL;
}

int main() {
    int choice, item = 0;
    pthread_t tid;

    sem_init(&empty, 0, BUFFER_SIZE);
    sem_init(&full, 0, 0);
    pthread_mutex_init(&mutex, NULL);

    while (1) {
        printf("\nEnter your choice 1.Producer 2.Consumer 3.Exit\n");
        scanf("%d", &choice);

        if (choice == 1) {
            item++;
            pthread_create(&tid, NULL, producer, &item);
            pthread_join(tid, NULL);
        } else if (choice == 2) {
            if (top == -1) {
                printf("Buffer is empty!!\n");
            } else {
                pthread_create(&tid, NULL, consumer, NULL);
                pthread_join(tid, NULL);
            }
        } else if (choice == 3) {
            break;
        } else {
            printf("Invalid choice!\n");
        }
    }

    sem_destroy(&empty);
    sem_destroy(&full);
    pthread_mutex_destroy(&mutex);

    return 0;
}
