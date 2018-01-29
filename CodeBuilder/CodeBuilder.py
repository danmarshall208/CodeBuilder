import random, sys
import io
import contextlib
import time
from multiprocessing import Pool, Queue, TimeoutError
from fuzzywuzzy import fuzz
from Valids import valid_func_names, valid_var_names, valid_funcs, operations, objects

@contextlib.contextmanager
def stdoutIO(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = io.StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old

def build_object():
    object_type = random.choice(objects)

    if object_type == 'int':
        code = str(random.randint(0, 100))

    if object_type == 'string':
        character = chr(random.randint(0, 150))        
        code = '"{}"'.format(character)

    if object_type == 'var':
        code = random.choice(valid_var_names)
                
    if object_type == 'function':
        function = random.choice(valid_funcs)
        function_input = build_object()
        code = '{}({})'.format(function, function_input)

    return code

def build_code_operation(operation):
    if operation == 'object':
        code = build_object()
        
    if operation == 'add':
        code = '{} + {}'.format(build_object(), build_object())

    if operation == 'subtract':
        code = '{} - {}'.format(build_object(), build_object())

    if operation == 'multiply':
        code = '{} * {}'.format(build_object(), build_object())

    if operation == 'divide':
        code = '{} / {}'.format(build_object(), build_object())

    if operation == 'equals':
        code = '{} == {}'.format(build_object(), build_object())

    if operation == 'not_equals':
        code = '{} != {}'.format(build_object(), build_object())

    return code

def generate_code(input_lines):
    # setup
    max_lines = 20
    lines_to_edit = 2
    lines = list(input_lines)

    # generate code
    for i in range(lines_to_edit):
        code_string = ""

        # remove a line
        if len(lines) > 10:
            if random.random() < 0.1:
                line_to_edit = random.randint(0, len(lines)-1)
                lines.pop(line_to_edit)
                return lines

        # assign to variable
        do_assignment = True #bool(random.getrandbits(1))
        if do_assignment:
            code_string += "{} = ".format(random.choice(valid_var_names))

        operation = random.choice(operations)
        code_string += build_code_operation(operation)
        code_string += "\n"

        if len(lines) < max_lines:
            overwrite = bool(random.getrandbits(1))
        else:
            overwrite = True

        if overwrite:
            line_to_edit = random.randint(0, len(lines)-1)
            lines[line_to_edit] = code_string
        else:
            line_to_insert = random.randint(0, len(lines))
            lines.insert(line_to_insert, code_string)

    return lines

# This is a Queue that behaves like stdout
class StdoutQueue():
    def __init__(self, *args, **kwargs):
        self.queue = Queue()

    def write(self, msg):
        self.queue.put(msg)

    def flush(self):
        sys.__stdout__.flush()

def map_stdout(new_stdout):
    sys.stdout = new_stdout

def functionize_code(lines):
    function_lines = list(lines)
    for index in range(len(function_lines)):
        lines[index] = '    ' + lines[index]

    code = "".join(lines)
    code = "def run():\n" + code

    return code

def run_code(lines, pool, process_stdout):
    execution_time = 1

    # assemble code
    #code = functionize_code(lines)
    #exec(code)
    code = ''.join(lines)

    # run code
    try:
        start_time = time.clock()
        result = pool.apply_async(exec, (code,{}))
        result.get(0.5)
        finish_time = time.clock()

        error = False
        recreate_pool = False
        execution_time = finish_time - start_time

    except TimeoutError:
        pool.terminate()
        pool.join()
        print("Timeout!")
        error = True
        recreate_pool = True

    except Exception as e:
        error = True
        recreate_pool = False

    output = ""
    while not process_stdout.queue.empty():
        output_line = process_stdout.queue.get()
        if not output_line == '\n':
            output += output_line

    return output, execution_time, error, recreate_pool

def score_function(output, execution_time):
    if len(output) < 10000:
        #return abs(10-sum(ord(ch) for ch in output))
        return fuzz.ratio("Hello world!", output) #- execution_time
    else:
        return 0

# main
if __name__ == '__main__':
    start_filename = "Code.py"
    result_filename = "Code.py"
    current_score = 0

    # read from file
    start_file = open(start_filename)
    lines = []
    for line in start_file:
        lines.append(line)
    start_file.close()

    # setup worker pool
    process_stdout = StdoutQueue()
    pool = Pool(1, map_stdout, (process_stdout,))

    # generations
    for i in range(1000000000):
        attempt = 0
        error = True

        while error == True:
            attempt += 1
            new_lines = generate_code(lines)
            output, execution_time, error, recreate_pool = run_code(new_lines, pool, process_stdout)

            if recreate_pool:
                pool = Pool(1, map_stdout, (process_stdout,))

        if i % 100 == 0:
            print("Generation {}: attempts {}".format(i, attempt))                

        new_score = score_function(output, execution_time)
        if new_score >= current_score:
            lines = new_lines

        if new_score > current_score:
            print("Generation {}:".format(i))
            print("Score: " + str(new_score))
            current_score = new_score
            current_best_output = output
            print("Output:")
            print(output)
            print("Current code:")
            for line in lines:
                print(line)
            print('\n')

        if i % 10000 == 0:
            try:
                result_file = open(result_filename, 'w')
                for line in lines:
                    result_file.write(line)
                result_file.close()
            except:
                result_file.close()

    print("Generation {}:".format(i))
    print("Score: " + str(current_score))
    print("Output:")
    print(current_best_output)
    print("Current code:")
    for line in lines:
        print(line)
    print('\n')

    result_file = open(result_filename, 'w')
    for line in lines:
        result_file.write(line)
    result_file.close()

    #sys.exit()