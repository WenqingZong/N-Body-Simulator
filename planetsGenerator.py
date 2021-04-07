import pickle
import sys
from n_body import Planet


def main():
    try:
        number = int(sys.argv[1])
        if number >= 0:
            planets = []
            for _ in range(number):
                planets.append(Planet())

            with open("planets.pkl", "wb") as output:
                pickle.dump(planets, output)

            print(number, "planet(s) have been generated, the result is written to planets.pkl.")
        else:
            print("Nothing has been done.")
    except ValueError:
        print("Please check your input.")
    except IndexError:
        print("Please give exactly one argument.")


if __name__ == "__main__":
    main()
