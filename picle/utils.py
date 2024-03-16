import traceback


def run_print_exception(func):
    """Decorator to run function and print exception if error occured"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            tb = traceback.format_exc()
            print(f"Function {str(func)} execution error:\n{tb}")

    return wrapper
