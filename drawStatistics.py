import numpy as np
import matplotlib.pyplot as plt
import pickle

def normalRead(fileName):
    """
    Only read noOfPlanets and averageFPS
    """
    data = []
    try:
        with open(fileName, "rb") as file:
            data = pickle.load(file)
    except (FileNotFoundError, EOFError) as e:
        print(e)
        exit()
    noOfPlanets = []
    averageFPS = []

    for i in range(len(data)):
        noOfPlanets.append(data[i][0])
        averageFPS.append(data[i][3])

    return noOfPlanets, averageFPS


if __name__ == "__main__":
    cpuNoOfPlanets, cpuAverageFPS = normalRead("cpuData.pkl")
    gpuNoOfPlanets, gpuAverageFPS = normalRead("gpuData.pkl")

    data = []
    try:
        with open("statistics.pkl", "rb") as file:
            data = pickle.load(file)
            # Tuples as sorted by first element by default.
            data.sort()
    except (EOFError, FileNotFoundError) as e:
        print(e)
        exit()

    noOfPlanets = []
    averageFPS = []

    allEffect = []
    noEffect = []
    onlySphere = []
    onlyTail = []
    # [(noOfPlanets, usePoint, withTail, FPS)]
    for i in range(len(data)):
        noOfPlanets.append(data[i][0])
        averageFPS.append(data[i][3])
        if data[i][1] and not data[i][2]:
            noEffect.append(i)
        elif data[i][1] and data[i][2]:
            onlyTail.append(i)
        elif not data[i][1] and data[i][2]:
            allEffect.append(i)
        elif not data[i][1] and not data[i][2]:
            onlySphere.append(i)

    noOfPlanets = np.array(noOfPlanets)
    onlyTail = np.array(onlyTail)
    onlySphere = np.array(onlySphere)
    averageFPS = np.array(averageFPS)

    # Draw
    plt.plot(cpuNoOfPlanets, cpuAverageFPS, "r--", label="Only CPU")
    plt.plot(gpuNoOfPlanets, gpuAverageFPS, "g--", label="Only GPU")
    plt.title("Influence of Number of Planets (Only CPU and Only GPU)")
    plt.xlabel("noOfPlanets")
    plt.ylabel("average FPS")
    plt.legend()
    plt.show()

    plt.plot(noOfPlanets[noEffect], averageFPS[noEffect], "r--", label="No Effect")
    plt.plot(noOfPlanets[onlySphere], averageFPS[onlySphere], "g--", label="Only Sphere")
    plt.title("Influence of Using Solid Sphere")
    plt.xlabel("noOfPlanets")
    plt.ylabel("average FPS")
    plt.legend()
    plt.show()

    plt.plot(noOfPlanets[noEffect], averageFPS[noEffect], "r--", label="No Effect")
    plt.plot(noOfPlanets[noEffect], averageFPS[onlyTail], "g--", label="Only Tail")
    plt.title("Influence of Show Tails")
    plt.xlabel("noOfPlanets")
    plt.ylabel("average FPS")
    plt.legend()
    plt.show()

    plt.plot(noOfPlanets[noEffect], averageFPS[noEffect], "r--", label="No Effect")
    plt.plot(noOfPlanets[allEffect], averageFPS[allEffect], "g--", label="All Effect")
    plt.title("Influence of All Effect")
    plt.xlabel("noOfPlanets")
    plt.ylabel("average FPS")
    plt.legend()
    plt.show()

