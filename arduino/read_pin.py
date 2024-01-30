
def read_pin():
  for i in range(1000):
    print(btn.value, end='', flush=True)
    if i % 10 == 0:
      print()
    time.sleep(0.1)

read_pin()
