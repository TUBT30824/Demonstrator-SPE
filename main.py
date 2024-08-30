import os
import sys
import datetime
import re
import time
import tkinter as tk
from tkinter import ttk
import threading
import random
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("environment variable SUMO_HOME is missing")

import sumolib
import traci
import osmWebWizard
import tls_manager

step = 0

steps = []
timelost_values = []
update_graph_active = False

all_routes = []
all_edges = []
current_emergencys = []
emergency_time = 0
stop_thread = False
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)



def listen_to_port():
    global stop_thread
    global s
    port = 12345
    s.bind(('', port))
    s.listen(1)


    while not stop_thread:
        print("waiting for connection")
        try:
            c, addr = s.accept()
        except OSError:
            break
        print('Connected by', addr)
        while not stop_thread:
            try:
                data = c.recv(1024)
                data = data.decode('utf-8')
                if not data:
                    print("Connection closed by client")
                    break
                output = parse_input(data)
                if output:
                    c.sendall(output.encode('utf-8'))
            except ConnectionResetError as e:
                print(e)
                c.close()
                break
            except OSError as e:
                print(e)
                c.close()
                break
        print("Connection closed")
        c.close()




def create_window():
    tls = tls_manager.tls_manager()

    def stop_simulation():
        global update_graph_active
        update_graph_active = False
        btn_start["state"] = "normal"
        time.sleep(0.5)
        traci.close()
        sys.stdout.flush()

    def refresh_maps():
        scenario_select['values'] = os.listdir("C:/Users/jetmi/PycharmProjects/BT/data")

    def manager_start():
        tls.connect()
        tls.start()

    def manager_stop():
        tls.stop()

    def update_graph():
        if not update_graph_active:
            return
        lbltxt_emergency_time.set(str(int(emergency_time)))
        ax.clear()
        ax.plot(steps, timelost_values)
        canvas.draw()
        window.after(200, update_graph)

    def start_graph():
        global update_graph_active
        update_graph_active = True
        update_graph()

    def tls_manager_on():
        user_input = tls_entry.get()
        if user_input[-3:] == "all":
            switch_all_tls(True)
        else:
            switch_tls(user_input[-2:], True)

    def tls_manager_off():
        user_input = tls_entry.get()
        if user_input[-3:] == "all":
            switch_all_tls(False)
        else:
            switch_tls(user_input[-2:], False)

    def block_lane():
        lane = lane_entry.get()
        set_blocked_lane(lane, True)

    def unblock_lane():
        lane = lane_entry.get()
        set_blocked_lane(lane, False)

    def send_emergency():
        lane = emergency_entry.get()
        fix_lane_emergency(lane)

    def start_osm():
        parser = sumolib.options.ArgumentParser(description="OSM Web Wizard for SUMO - Websocket Server")
        parser.add_argument("--remote", action="store_true",
                            help="In remote mode, SUMO GUI will not be automatically opened instead a zip file " +
                                 "will be generated.")
        parser.add_argument("--osm-file", default="osm_bbox.osm.xml", dest="osmFile", help="use input file from path.")
        parser.add_argument("--test-output", dest="testOutputDir",
                            help="Run with pre-defined options on file 'osm_bbox.osm.xml' and " +
                                 "write output to the given directory.")
        parser.add_argument("--bbox", help="bounding box to retrieve in geo coordinates west,south,east,north.")
        parser.add_argument("-o", "--output", dest="outputDir",
                            help="Write output to the given folder rather than creating a name based on the timestamp")
        parser.add_argument("--address", default="", help="Address for the Websocket.")
        parser.add_argument("--port", type=int, default=8010,
                            help="Port for the Websocket. Please edit script.js when using an other port than 8010.")
        parser.add_argument("-v", "--verbose", action="store_true", default=False, help="tell me what you are doing")
        parser.add_argument("-b", "--begin", default=0, type=sumolib.miscutils.parseTime,
                            help="Defines the begin time for the scenario.")
        parser.add_argument("-e", "--end", default=1000000, type=sumolib.miscutils.parseTime,
                            help="Defines the end time for the scenario.")
        parser.add_argument("-n", "--netconvert-options", help="additional comma-separated options for netconvert")
        parser.add_argument("--demand", default="passenger:30f12,bicycle:2f2,pedestrian:4,ship:1f40",
                            help="Traffic demand definition for non-interactive mode.")
        osmWebWizard.main(parser.parse_args(
            "-o C:/Users/jetmi/PycharmProjects/BT/data/" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))

    def run_osm():
        threading.Thread(target=start_osm).start()

    def on_closing():
        global stop_thread
        global s
        stop_thread = True
        tls.stop()
        window.destroy()
        s.close()


    global scenario_select
    global btn_start
    global window
    global socket_entry
    global socket_checkbox_state
    window = tk.Tk()
    window.title("Simulation Control Panel")
    window.geometry("310x520")
    window.grid_rowconfigure(1, minsize=20)
    window.grid_rowconfigure(3, minsize=20)

    lbltxt_emergency_time = tk.StringVar()

    btn_start = tk.Button(window, text="Start the simulation", width=20, height=5, command=run_simulation)
    btn_end = tk.Button(window, text="End the simulation", width=20, height=5, command=stop_simulation)
    btn_osm = tk.Button(window, text="Create Own Scenario", width=20, height=1, command=run_osm)
    btn_osm.config(bg='blue')  # Change the color of the btn_osm button

    btn_refreshmap = tk.Button(window, text="Refresh Maps", width=10, height=1, command=refresh_maps)

    scenario_select = ttk.Combobox(window, values=os.listdir("C:/Users/jetmi/PycharmProjects/BT/data"))
    scenario_select.set("9x9")
    tls_entry = tk.Entry(window, width=20)
    btn_tls_off = tk.Button(window, text="TLS Off", width=10, height=1, command=tls_manager_off)
    btn_tls_on = tk.Button(window, text="TLS On", width=10, height=1, command=tls_manager_on)
    lane_entry = tk.Entry(window, width=20)
    btn_block_lane = tk.Button(window, text="Block Lane", width=10, height=1, command=block_lane)
    btn_unblock_lane = tk.Button(window, text="Unblock Lane", width=10, height=1, command=unblock_lane)
    emergency_entry = tk.Entry(window, width=20)
    btn_send_emergency = tk.Button(window, text="Emergency", width=10, height=1, command=send_emergency)
    lbl_emergency_time = tk.Label(window, textvariable=lbltxt_emergency_time, width=10, height=1)
    btn_showstats = tk.Button(window, text="Show Timeloss", width=20, height=1, command=start_graph)
    btn_manger_start = tk.Button(window, text="Start TLS Manager", width=20, height=1, command=manager_start)
    btn_manager_stop = tk.Button(window, text="Stop TLS Manager", width=20, height=1, command=manager_stop)
    socket_entry = tk.Entry(window, width=20)
    socket_entry.insert(0, "localhost:9879")
    socket_checkbox_state = tk.IntVar()
    socket_checkbox = tk.Checkbutton(window, text="Full Output", variable=socket_checkbox_state)

    fig = Figure(figsize=(3, 2), dpi=100)
    ax = fig.add_subplot()
    canvas = FigureCanvasTkAgg(fig, master=window)  # 'window' is your Tkinter window
    canvas_widget = canvas.get_tk_widget()

    btn_start.grid(row=0, column=0, columnspan=2)
    btn_end.grid(row=0, column=2, columnspan=2)
    scenario_select.grid(row=2, column=0, columnspan=3, sticky='ew')
    btn_refreshmap.grid(row=2, column=3, sticky='ew')
    socket_entry.grid(row=3, column=0, columnspan=2)
    socket_checkbox.grid(row=3, column=2, columnspan=2)
    btn_osm.grid(row=4, column=0, columnspan=2)
    tls_entry.grid(row=5, column=0, columnspan=2)
    btn_tls_on.grid(row=5, column=2, columnspan=1)
    btn_tls_off.grid(row=5, column=3, columnspan=1)
    lane_entry.grid(row=6, column=0, columnspan=2)
    btn_block_lane.grid(row=6, column=2, columnspan=1)
    btn_unblock_lane.grid(row=6, column=3, columnspan=1)
    emergency_entry.grid(row=7, column=0, columnspan=2)
    btn_send_emergency.grid(row=7, column=2, columnspan=1)
    lbl_emergency_time.grid(row=7, column=3, columnspan=1)
    btn_showstats.grid(row=8, column=0, columnspan=4)
    canvas_widget.grid(row=9, column=0, columnspan=4)
    btn_manger_start.grid(row=10, column=0, columnspan=2)
    btn_manager_stop.grid(row=10, column=2, columnspan=2)

    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.mainloop()

    return

def get_current_timeloss(vehicles=None):
    if vehicles is None:
        try:
            vehicles = traci.vehicle.getIDList()
        except traci.exceptions.FatalTraCIError:
            return 0
    cars_not_found = 0

    total_timelost = 0
    for car in vehicles:
        try:
            total_timelost += traci.vehicle.getTimeLoss(car)
        except traci.exceptions.TraCIException:
            cars_not_found += 1

    if len(vehicles) > 0:
        avg_timelost = total_timelost / (len(vehicles) - cars_not_found)
    else:
        avg_timelost = 0
    return avg_timelost


def update_graph_values(vehicles=None):
    if vehicles is None:
        try:
            vehicles = traci.vehicle.getIDList()
        except traci.exceptions.FatalTraCIError:
            return 0
    if not update_graph_active:
        return
    if len(steps) > 200:
        steps.pop(0)
    if len(timelost_values) > 200:
        timelost_values.pop(0)
    timelost_values.append(get_current_timeloss(vehicles))
    steps.append(step)

    global emergency_time
    emergency_time_temp = 0
    for ce in current_emergencys:
        if ce[0] in vehicles:
            emergency_time_temp += traci.vehicle.getTimeLoss(ce[0])
    if emergency_time_temp > 0:
        emergency_time = emergency_time_temp


def update_traffic_demand():
    current_cars = traci.vehicle.getIDCount()
    if current_cars < 400:
        sq_insert_vehicle(4)


def get_all_edges():
    edges = []
    for e in traci.edge.getIDList():
        if e[0] != ':':
            edges.append(e)
    return edges


def create_random_routes():
    routes = []
    for i in range(0, 1000):
        start = random.randrange(0, len(all_edges))
        end = random.randrange(0, len(all_edges))
        routes.append([i, [all_edges[start], all_edges[end]], all_edges[end] + "_0"])
        traci.route.add(i, [all_edges[start], all_edges[end]])
    return routes


def sim_sq_run():
    global btn_start
    btn_start["state"] = "disabled"
    global step
    step = 0
    global stop_thread
    select = scenario_select.get()
    if socket_checkbox_state.get() == 1:
        traci.start(
            ["sumo-gui", "--start", "-c", "data/" + select + "/osm.sumocfg", "--fcd-output",
             socket_entry.get(), "--step-length", "0.05", "-t"],
            label="sim")
    else:
        traci.start(
            ["sumo-gui", "--start", "-c", "data/" + select + "/osm.sumocfg", "--step-length", "0.05", "-t"],
            label="sim")

    global all_edges
    all_edges = get_all_edges()
    global all_routes
    all_routes = create_random_routes()

    if select != "9x9":
        add_vehicle_type("type1", "passenger", 1.7,4.5,  4.074, 1.751, 2.5, 47.5, "HBEFA4/PC_petrol_Euro-6d",
                         "passenger/hatchback", "1,0,0")
        add_vehicle_type("type2", "passenger", 2.7,  4.5,  4.505, 1.816, 2.5, 58.3, "HBEFA4/PC_diesel_Euro-6d",
                         "passenger/sedan", "0,1,0")
        add_vehicle_type("type3", "passenger", 4.9,  4.5,  4.783, 1.852, 2.5, 52.7, "HBEFA4/PC_BEV",
                         "passenger/sedan", "0,0,1", {"has.battery.device": "true"})
        add_vehicle_type("type4", "delivery", 1.1,  4.5,  5.932, 2.331, 2.5, 41.6,
                         "HBEFA4/LCV_diesel_N1-III_Euro-6d", "delivery", "0,1,1")
        add_vehicle_type("type0", "emergency", 1.7,  4.5,  5.932, 2.331, 2.5, 41.6,
                         "HBEFA4/LCV_diesel_N1-III_Euro-6d", "emergency", "1,0,1", {"has.bluelight.device": "true"})

    while step < 1000000 and not stop_thread:
        if btn_start["state"] == "normal":
            return
        try:
            traci.simulationStep()
        except OSError:
            return
        except traci.exceptions.FatalTraCIError:
            return

        #TODO: maybe use steplistener instead to better performance
        if step % 30 == 0:
            vehicles = traci.vehicle.getIDList()
            if update_graph_active:
                update_graph_values(vehicles)
            for e in vehicles:
                if not traci.vehicle.isRouteValid(e):
                    try:
                        if not traci.vehicle.getNextLinks(e):
                            reroute_blocked_vehicle(e)
                    except:
                        continue
            update_traffic_demand()
            if step % 60 == 0:
                for ce in current_emergencys:
                    if has_vehicle_arrived(ce[0], vehicles):
                        set_blocked_lane(ce[1], False)
                        current_emergencys.remove(ce)
        step += 1
    traci.close()
    sys.stdout.flush()


def run_simulation():
    sim_thread = threading.Thread(target=sim_sq_run)
    sim_thread.start()

# if destination is not reachable for vehicle, reroute vehicle to edge on the other site of the road, if destination is
# reachable, reroute vehicle to same destination via different route

# for every map: if other side doesnt work, reroute to lane connected to destination lane
def reroute_blocked_vehicle(vehicle):
    route = traci.vehicle.getRoute(vehicle)
    destination = route[len(route) - 1]
    if "passenger" not in traci.lane.getAllowed(destination + "_0"):
        traci.vehicle.changeTarget(vehicle, destination[2:] + destination[:2])
    else:
        traci.vehicle.changeTarget(vehicle, destination)



def switch_all_tls(active):
    for tls in traci.trafficlight.getIDList():
        switch_tls(tls, active)
    return


def switch_tls(name, active):
    if active:
        traci.trafficlight.setProgram(name, "0")
    else:
        traci.trafficlight.setProgram(name, "off")



def insert_emergency_vehicle(destination):
    id = "Emergency-" + str(step)
    traci.vehicle.add(id, "emergency_start", 'type0', "now",
                      "random",
                      "random", 0, "random", "random")
    if destination[-2:] == "_0":
        destination = destination[:-2]
    traci.vehicle.changeTarget(id, destination)
    return id


def fix_lane_emergency(lane):
    global current_emergencys
    current_emergencys.append([insert_emergency_vehicle(lane), lane])


def has_vehicle_arrived(vehicle_id, active_vehicles=None):
    if active_vehicles is None:
        active_vehicles = traci.vehicle.getIDList()
    return vehicle_id not in active_vehicles


def add_vehicle_type(type_id, vClass, accel, decel, length, width, minGap, maxSpeed, emissionClass,
                     guiShape, color, additional_params=None):
    traci.vehicletype.copy("DEFAULT_VEHTYPE", type_id)
    traci.vehicletype.setVehicleClass(type_id, vClass)
    traci.vehicletype.setAccel(type_id, accel)
    traci.vehicletype.setDecel(type_id, decel)
    traci.vehicletype.setLength(type_id, length)
    traci.vehicletype.setWidth(type_id, width)
    traci.vehicletype.setMinGap(type_id, minGap)
    traci.vehicletype.setMaxSpeed(type_id, maxSpeed)
    traci.vehicletype.setEmissionClass(type_id, emissionClass)
    traci.vehicletype.setShapeClass(type_id, guiShape)
    colorparts = color.split(",")
    traci.vehicletype.setColor(type_id, (int(colorparts[0])*250, int(colorparts[1])*250, int(colorparts[2])*250))
    if additional_params:
        for key, value in additional_params.items():
            traci.vehicletype.setParameter(type_id, key, value)


def sq_insert_vehicle(count):
    while count > 0:
        x = random.randrange(1, 5)
        y = random.randrange(0, len(all_routes))

        if traci.lane.getAllowed(all_routes[y][2]):
            if "passenger" not in traci.lane.getAllowed(all_routes[y][2]):
                continue
        try:
            traci.vehicle.add("Car-" + str(step) + "-" + str(count), all_routes[y][0], 'type' + str(x), "now",
                              "random",
                              "random", 0, "random", "random")
        except traci.exceptions.TraCIException:
            print("Error:" + str(all_routes[y][1]))
        count = count - 1


def set_blocked_lane(lane, blocked):
    if blocked:
        traci.lane.setAllowed(lane, ["emergency"])
    else:
        traci.lane.setDisallowed(lane, [])


def parse_input(user_input):
    answer = "done"
    global stop_thread
    global btn_start
    if stop_thread:
        return
    if user_input == "exit":
        sys.exit()
    if user_input == "help":
        return "Available commands: \n" \
                "stat - Get the current ATL\n" \
                "insertCar - Insert a random car\n" \
                "tls_switchOn_all - Switch all traffic lights on\n" \
                "tls_switchOff_all - Switch all traffic lights off\n" \
                "tls_switchOn_[id] - Switch traffic light with [id] on\n" \
                "tls_switchOff_[id] - Switch traffic light with [id] off\n" \
                "tls_getPhase_[id] - Get phase of traffic light with [id]\n" \
                "tls_setPhase_[id]_[phase] - Set phase of traffic light with [id] to [phase]\n" \
                "tls_getControlledLanes_[id] - Get which lanes of traffic light with [id] controlls\n" \
                "tls_getProgram_[id] - Get program of traffic light with [id]\n" \
                "tls_setProgram_[id]_[programID] - Set program of traffic light with [id] to [programID]\n" \
                "tls_getRedYellowGreenState_[id] - Get current state of traffic light with [id]\n" \
                "tls_setRedYellowGreenState_[id]_[state] - Set state of traffic light with [id] to [state] in the format ryg\n" \
                "lane_block_[id] - Block lane with [id]\n" \
                "lane_open_[id] - Open lane with [id]\n" \
                "lane_VehicleNumber_[id] - Get the number of vehicles on lane with [id]\n" \
                "lane_getEdgeID_[id] - Get the edge ID of lane with [id] to which it belongs\n" \
                "lane_getLength_[id] - Get length of lane with [id] in meters\n" \
                "lane_getNoiseEmission_[id] - Get noise emission in the lane with [id]\n" \
                "lane_getCO2Emission_[id] - Get CO2 emission in the lane with [id]\n" \
                "vehicle_getLaneID_[id] - Get the laneID on which it is currently driving of vehicle with [id]\n" \
                "vehicle_getPosition_[id] - Get position of vehicle with [id] as x,y coordinates\n" \
                "vehicle_getNextTLS_[id] - Get the next TLS it is going to encounter on its route of vehicle with [id]\n" \
                "vehicle_getRoute_[id] - Get the route of vehicle with [id] as a list of edges\n" \
                "vehicle_setRoute_[id]_[route] - Set the route of vehicle with [id] to [route] in the format list<edges>\n" \
                "vehicle_getSpeed_[id] - Get the current speed of vehicle with [id]\n" \
                "vehicle_getTimeloss_[id] - Get the timeloss of vehicle with [id]\n" \
                "vehicle_getTypeID_[id] - Get the vehicle-type ID of vehicle with [id]\n" \
                "vehicle_isStoppedParking_[id] - Get information on if a vehicle with [id] is stopped parking\n"
    if btn_start["state"] == "normal":
        return "While the simulation is not running, you can only use the help command" \

    patterns = {
        "tls": r"^tls_.*_.*$",
        "switchOn": r"^.*_switchOn_.*$",
        "switchOff": r"^.*_switchOff_.*$",
        "getphase": r"^.*_getPhase_.*$",
        "setphase": r"^.*_setPhase_.*_.*$",
        "getControlledLanes": r"^.*_getControlledLanes_.*$",
        "getProgram": r"^.*_getProgram_.*$",
        "setProgram": r"^.*_setProgram_.*_.*$",
        "getRedYellowGreenState": r"^.*_getRedYellowGreenState_.*$",
        "setRedYellowGreenState": r"^.*_setRedYellowGreenState_.*_.*$",
        "lane": r"^lane_.*$",
        "block": r"^.*_block_.*$",
        "open": r"^.*_open_.*$",
        "vehicle_number": r"^.*_VehicleNumber_.*$",
        "getEdgeID": r"^.*_getEdgeID_.*$",
        "getLength": r"^.*_getLength_.*$",
        "getNoiseEmission": r"^.*_getNoiseEmission_.*$",
        "getCO2Emission": r"^.*_getCO2Emission_.*$",
        "vehicle": r"^vehicle_.*$",
        "getLaneID": r"^.*_getLaneID_.*$",
        "getPosition": r"^.*_getPosition_.*$",
        "getNextTLS": r"^.*_getNextTLS_.*$",
        "getRoute": r"^.*_getRoute_.*$",
        "setRoute": r"^.*_setRoute_.*_.*$",
        "getSpeed": r"^.*_getSpeed_.*$",
        "getTimeloss": r"^.*_getTimeloss_.*$",
        "getTypeID": r"^.*_getTypeID_.*$",
        "isStoppedParking": r"^.*_isStoppedParking_.*$",
        "stat": r"^stat$",
        "insertCar": r"^insertCar$"
    }

    if re.match(patterns["stat"], user_input):
        return "ATL= " + traci.simulation.getParameter(objectID="", key="device.tripinfo.vehicleTripStatistics.waitingTime")
    elif re.match(patterns["insertCar"], user_input):
        sq_insert_vehicle(1)
        return "Car inserted"

    last_us_index = user_input.rfind('_')
    if last_us_index == -1:
        return "Error - Enter a valid command"
    slast_us_index = user_input.rfind('_', 0, last_us_index)
    if slast_us_index == -1:
        return "Error - Enter a valid command"
    last_param = user_input[last_us_index + 1:]
    slast_param = user_input[slast_us_index + 1:last_us_index]

    if re.match(patterns["lane"], user_input):
        if re.match(patterns["block"], user_input):
            set_blocked_lane(last_param, True)
        elif re.match(patterns["open"], user_input):
            set_blocked_lane(last_param, False)
        elif re.match(patterns["vehicle_number"], user_input):
            answer = traci.lane.getLastStepVehicleNumber(last_param)
        elif re.match(patterns["getEdgeID"], user_input):
            answer = traci.lane.getEdgeID(last_param)
        elif re.match(patterns["getLength"], user_input):
            answer = traci.lane.getLength(last_param)
        elif re.match(patterns["getNoiseEmission"], user_input):
            answer = traci.lane.getNoiseEmission(last_param)
        elif re.match(patterns["getCO2Emission"], user_input):
            answer = traci.lane.getCO2Emission(last_param)
    elif re.match(patterns["tls"], user_input):
        if re.match(patterns["switchOn"], user_input):
            if last_param == "all":
                switch_all_tls(True)
            else:
                switch_tls(last_param, True)
        elif re.match(patterns["switchOff"], user_input):
            if last_param == "all":
                switch_all_tls(False)
            else:
                switch_tls(last_param, False)
        elif re.match(patterns["getphase"], user_input):
            answer = traci.trafficlight.getPhase(last_param)
        elif re.match(patterns["setphase"], user_input):
            traci.trafficlight.setPhase(slast_param, last_param)
        elif re.match(patterns["getControlledLanes"], user_input):
            answer = traci.trafficlight.getControlledLanes(last_param)
        elif re.match(patterns["getProgram"], user_input):
            answer = traci.trafficlight.getProgram(last_param)
        elif re.match(patterns["setProgram"], user_input):
            traci.trafficlight.setProgram(slast_param, last_param)
        elif re.match(patterns["getRedYellowGreenState"], user_input):
            answer = traci.trafficlight.getRedYellowGreenState(last_param)
        elif re.match(patterns["setRedYellowGreenState"], user_input):
            traci.trafficlight.setRedYellowGreenState(slast_param, last_param)
    elif re.match(patterns["vehicle"], user_input):
        if re.match(patterns["getLaneID"], user_input):
            answer = traci.vehicle.getLaneID(last_param)
        elif re.match(patterns["getPosition"], user_input):
            answer = traci.vehicle.getPosition(last_param)
        elif re.match(patterns["getNextTLS"], user_input):
            answer = traci.vehicle.getNextTLS(last_param)
        elif re.match(patterns["getRoute"], user_input):
            answer = traci.vehicle.getRoute(last_param)
        elif re.match(patterns["setRoute"], user_input):
            traci.vehicle.setRoute(slast_param, last_param)
        elif re.match(patterns["getSpeed"], user_input):
            answer = traci.vehicle.getSpeed(last_param)
        elif re.match(patterns["getTimeloss"], user_input):
            answer = traci.vehicle.getTimeLoss(last_param)
        elif re.match(patterns["getTypeID"], user_input):
            answer = traci.vehicle.getTypeID(last_param)
        elif re.match(patterns["isStoppedParking"], user_input):
            answer = traci.vehicle.isStoppedParking(last_param)

    return str(answer)

def listen():
    global stop_thread
    while not stop_thread:
        try:
            user_input = input("Enter command: ")
            print(parse_input(user_input))
        except EOFError:
            break


win_thread = threading.Thread(target=create_window)
input_thread = threading.Thread(target=listen)
listen_thread = threading.Thread(target=listen_to_port)

win_thread.start()
input_thread.start()
listen_thread.start()

input_thread.join()
listen_thread.join()
win_thread.join()
sys.exit()
