
import numpy as np
import matplotlib.pyplot as plt

data = np.loadtxt(
    "ngspice_interface/Simulation_Result/tran_TwoStage.csv",
    skiprows=1
)

time = data[:, 0] * 1e6
vin1 = data[:, 1]
vin2 = data[:, 2]
vout = data[:, 3]

plt.figure(figsize=(12, 6))

plt.plot(time, vin1, label="VIN+ (net1)")
plt.plot(time, vin2, label="VIN- (net2)")
plt.plot(time, vout, label="VOUT (net6)", linewidth=2)

plt.xlabel("Time (µs)")
plt.ylabel("Voltage (V)")
plt.title("Two-Stage Op-Amp: Transient Input and Output")
plt.xlim(0, 30)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
