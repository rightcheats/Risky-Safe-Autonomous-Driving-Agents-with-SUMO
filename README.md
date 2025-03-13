# Evaluating Autonomous Driving Agents with Differing (Safe vs Risky) Driving Styles

## Overview

Simulate a road network with ‘NPC’ vehicles, the aim of the intelligent agents is to get from point A to B. Two agents, SafeDriver and RiskyDriver will be implemented, both having different driving styles to maximise safety, and minimise journey time respectively.

## Environment 

Eclipse’s SUMO (Simulation of Urban Mobility), an open-source traffic simulation package with can generate the required roads and NPCs. 

## Agents

SafeDriver: avoid risk, follow all traffic rules, and prefer longer but safer routes. Low exploration, high exploitation. 
RiskyDriver: prioritise speed, taking shortcuts and aggressively overtaking, whilst ignoring some traffic rules e.g. would run a yellow light. High exploration and stochastic decision-making. 

*Exact implementation of this is still to be decided, but basic ideas of reinforcement learning, (Q-learning with epsilon-greedy and stochastic decision-making are being explored).*

## Question 

“How do different driving styles impact overall efficiency, journey time, and collision frequency in autonomous driving agents?”

## Experiments

-	Increase/decrease number of NPCs, see impact e.g. overtaking,
-	Measure average journey time and average number of collisions,
-	Measure who learns the route faster.
