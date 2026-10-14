import threading
import time

def countdown(start, thread_name):
    while start > 0:
        print(f"{thread_name} : {start}")
        start -= 1
        time.sleep(1)
    print(f"{thread_name} : 0")

thread1 = threading.Thread(target=countdown, args=(5, 'thread 1'))
thread1.start()

thread2 = threading.Thread(target=countdown, args=(3, 'thread 2'))
thread2.start()

thread1.join()
thread2.join()

print("Les deux threads ont terminé.")
