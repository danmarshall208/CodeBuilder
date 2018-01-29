from multiprocessing import Process

if __name__ == '__main__':
    code = 'print(8)\nprint(9)'
    proc = Process(target=exec, args=(code,))
    proc.start()
    proc.join()