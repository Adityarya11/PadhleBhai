#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

int main() {
    int fd[2];
    pid_t pid;
    char write_msg[] = "1234";
    char read_msg[10];

    if (pipe(fd) == -1) {
        perror("pipe failed");
        exit(1);
    }

    pid = fork();

    if (pid < 0) {
        perror("fork failed");
        exit(1);
    }

    if (pid == 0) {
        // Child process
        close(fd[0]); // close read end
        printf("Generating PIN in child and sending to parent...\n");
        write(fd[1], write_msg, strlen(write_msg) + 1);
        close(fd[1]);
    } else {
        // Parent process
        close(fd[1]); // close write end
        read(fd[0], read_msg, sizeof(read_msg));
        printf("Parent received PIN '%s'\n", read_msg);
        close(fd[0]);
    }

    return 0;
}
