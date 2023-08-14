# PCS-Teledyne
The Teledyne Agent and Client fit within the OCS framework developed by Simons Observatory.
The Teledyne Agent, using a serial connection, is able to gather pressure reading from the Teledyne pressure gauge connected to the large dilution refrigerator. The Teledyne Client makes use of this agent through the OCS framework, to control an Arduino Uno to open the needle-valve manifold, keeping the pressure rate within a safe magnitude.
