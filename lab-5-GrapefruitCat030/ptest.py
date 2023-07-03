from random import randint

def execute_function(probability, function_to_execute):
    randomint = randint(1,100)
    if randomint < probability*100:
        function_to_execute()

def my_function():
    print("Function executed!")

# Example usage
probability = 0.18
for _ in range(100):
    execute_function(probability, my_function)
