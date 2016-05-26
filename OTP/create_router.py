import os
from shutil import copy
from argparse import ArgumentParser
from subprocess import call

OTP_JAR='/opt/repos/OpenTripPlanner/target/otp-0.20.0-SNAPSHOT-shaded.jar'

def main():
    parser = ArgumentParser(description="OTP Routererzeugung")
    
    parser.add_argument("--folder", "-f", action="store",
                        help="folder with pbf and gtfs data",
                        dest="folder", required=True)
    
    parser.add_argument("--name", "-n", action="store",
                        help="name of the router",
                        dest="name", required=True)
    
    parser.add_argument("--graph_folder", "-g", action="store",
                        help="folder with graphs",
                        dest="graph_folder", required=True)    
    
    args = parser.parse_args()
    
    call(['java', '-Xmx2G', '-jar', OTP_JAR, '--build', args.folder])
    
    graph_file = os.path.join(args.folder, "Graph.obj")  
    target_folder = os.path.join(args.graph_folder, args.name)
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)
    copy(graph_file, target_folder)    

if __name__ == "__main__":
    main()