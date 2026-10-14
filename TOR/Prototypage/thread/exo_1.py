import threading
import time

def text(i):
    print(f"Je suis la thead {i}")

for i in range(5):
    t1 = threading.Thread(target=text, args=[1])
    t1.start()

    time.sleep(1)

    t2 = threading.Thread(target=text, args=[2])
    t2.start()

    t1.join()
    t2.join()
