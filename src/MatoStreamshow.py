import config

def main():
    if config.token == "":
        raise ValueError('config token not found')

if __name__ == "__main__":
    main()
