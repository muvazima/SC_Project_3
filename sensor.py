import random

# 1 Fuel
def FuelSensor():
    
    fuel=random.uniform(0, 100)
    return fuel

# 2 Proximity to another cars
def ProximitySensor():
    
    data = {'x': random.uniform(-45, 45), 'y': random.uniform(-45, 45)}
    proximity = (data['x'] ** 2 + data['y'] ** 2) ** 0.5
    return proximity


# 3 Power
def PowerSensor():
    
    power = random.uniform(0, 100)
    return power

# 4 Speed
def SpeedSensor():
    
    speed = random.randint(0, 80)
    return speed

# 5 Track path
def LocationSensor():
    
    l_x = random.uniform(-180, 180) #Starting point coordinates
    l_y = random.uniform(-90, 90)
        # so the location of this car is (l_x,l_y)

    rd = random.random() # direction
    if rd % 2 ==0:
        l_x += 1
    else:
        l_y += 1

    location = {'Latitude':l_x, 'Longitude': l_y}
        
    return location

# 6 Whether to change lanes
def LaneChangeSensor():

    list_string = [0,1]
    lanechange = random.choice(list_string)
    return lanechange


# 7 Distance from bottom to ground
def Obstacle():
   
    obstacle=random.uniform(0,50)
    return obstacle


# 8 Environmental brightness (Lx)
def Light():

    light=random.uniform(0.5, 5000)
    return light

#Actuator 1 - Check if Enough Fuel Available
def isEnoughFuelAvailable(Fuel):

    if(Fuel<5):
        return False
    return True

#Actuator 2 - Check if Obstacle Found
def isObstacleFound(Obstacle):
    if(Obstacle<10):
        return True
    return False