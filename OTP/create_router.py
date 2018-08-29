from __future__ import print_function
import os
from shutil import move
from argparse import ArgumentParser
from subprocess import call

OTP_JAR='/opt/OpenTripPlanner/otp-ggr-stable.jar'

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
    dst_file = os.path.join(target_folder, "Graph.obj")
    if os.path.exists(dst_file):
        os.remove(dst_file)
        print("overwriting old file...")
    move(graph_file, dst_file)
    print("Graph moved to " + dst_file)

if __name__ == "__main__":
    main()
