'''
Created on Mar 16, 2016

Batch processing of routes in OpenTripPlanner
to be used with Jython (Java Bindings!)

@author: Christoph Franke
'''
#!/usr/bin/jython

from java.text import SimpleDateFormat
from java.util import TimeZone
from org.opentripplanner.scripting.api import OtpsEntryPoint
from org.opentripplanner.scripting.api import OtpsAggregate, OtpsAccumulate
from config import (LONGITUDE_COLUMN, LATITUDE_COLUMN, DATETIME_FORMAT,
                    AGGREGATION_MODES, ACCUMULATION_MODES, OUTPUT_DATE_FORMAT)
from datetime import datetime
import csv
import os


class CSVWriter(object):
    '''
    Parameters
    ----------
    target_csv: filename of the file to write to
    oid: name of the field of the origin ids
    did: name of the field of the destination ids
    mode: optional, the aggregation or accumulation mode (see config.AGGREGATION_MODES resp. config.ACCUMULATION_MODES)
    field: optional, the field to aggregate/accumulate
    params: optional, params needed by the aggregation/accumulation mode (e.g. thresholds)
    write_dest_data: optional, if True write the original columns of the destinations to the target_csv
    calculate_details: optional, if True write details like departure and arrival time to target_csv
    '''
    def __init__(self, target_csv, oid, did, mode, field,
                 params, bestof=None, arrive_by=False,
                 write_dest_data=False, calculate_details=False):
        self.oid = oid
        self.did = did
        self.target_csv = target_csv
        self.arrive_by = arrive_by
        self.write_dest_data = write_dest_data
        self.bestof = bestof
        self.mode = mode
        self.field = field
        self.params = params
        self.calculate_details = calculate_details
        if os.path.exists(target_csv):
            os.remove(target_csv)

    def write(self, result_sets, append=True, additional_columns={}):
        '''
        write result sets to csv file, may aggregate/accumulate before writing results

        Parameters
        ----------
        result_sets: list of result_sets
        append: optional, if True append results to target_csv, else overwrite
        additional_columns: optional, dict with column-names/values as key/value pairs
        '''
        print 'post processing results...'

        if len(result_sets) == 0:
            return
        header = [ 'origin id' ]
        do_aggregate = do_accumulate = False
        if not self.mode:
            header += [ 'destination id', 'travel time (sec)'] + additional_columns.keys()
            if self.calculate_details:
                details = ['boardings', 'walk/bike distance (m)',
                           'start time', 'arrival time', 'start transit', 'arrival transit', 'distance (m)',
                           'transit time', 'traverse modes', 'waiting time (sec)', 'elevation gained (m)',
                           'elevation lost (m)']
                header += details
        elif self.mode in AGGREGATION_MODES.keys():
            header += [self.field + '-aggregated']
            do_aggregate = True
        elif self.mode in ACCUMULATION_MODES.keys():
            header += [self.field + '-accumulated']
            do_accumulate = True

        # add header for data of destinations
        if self.write_dest_data and not (do_accumulate or do_aggregate):
            # all results share the same data names, cause they originate from the same csv file
            # you just have to find a valid result
            for i, res in enumerate(result_sets):
                if res is None:
                    continue
                if self.arrive_by:
                    data_fields = result_sets[i].getRoot().getDataFields()
                else:
                    data_fields = result_sets[i].getPopulation().getDataFields()
                data_fields.remove(self.did)
                for field in data_fields:
                    header.append('destination_' + field)
                break # found one -> break

        write_header = True
        if not append:
            fmode = 'wb'
        else:
            fmode = 'a'
            if os.path.exists(self.target_csv):
                write_header = False

        with open(self.target_csv, fmode) as f_csv:
            writer = csv.writer(f_csv, delimiter=';')

            if write_header:
                writer.writerow(header)

            if do_accumulate:
                accumulator = OtpsAccumulate(self.mode, self.params)

            for result_set in result_sets:
                if result_set is None:
                    continue

                if do_accumulate:
                    amount = result_set.getRoot().getFloatData(self.field)
                    accumulator.accumulate(result_set, amount)
                    continue

                if self.arrive_by:
                    destination = result_set.getRoot()
                    dest_id = destination.getStringData(self.did)
                else:
                    origin_id = result_set.getRoot().getStringData(self.oid)

                if do_aggregate:
                    aggregator = OtpsAggregate(self.mode, self.params)
                    aggregated = aggregator.aggregate(result_set, self.field)
                    # origin_id is known here, because !arriveby when aggregating
                    writer.writerow([origin_id, aggregated])

                else:
                    if self.bestof is not None:
                        results = result_set.getBestResults(self.bestof)
                    else:
                        results = result_set.getResults();

                    for result in results:

                        if result is None: #unreachable
                            continue

                        if self.arrive_by:
                            origin_id = result.getIndividual().getStringData(self.oid)
                        else:
                            destination = result.getIndividual()
                            dest_id = destination.getStringData(self.did)

                        row = [origin_id,
                               dest_id,
                               result.getTime()]
                        if additional_columns:
                            row += additional_columns.values()
                        if self.calculate_details:
                            details = [result.getBoardings(),
                                       result.getWalkDistance(),
                                       result.getStartTime(OUTPUT_DATE_FORMAT),
                                       result.getArrivalTime(OUTPUT_DATE_FORMAT),
                                       result.getStartTransit(OUTPUT_DATE_FORMAT),
                                       result.getArrivalTransit(OUTPUT_DATE_FORMAT),
                                       result.getDistance(),
                                       result.getTransitTime(),
                                       result.getModes(),
                                       result.getWaitingTime(),
                                       result.getElevationGained(),
                                       result.getElevationLost()]
                            row += details

                        if self.write_dest_data:
                            for field in data_fields:
                                row.append(destination.getStringData(field))

                        writer.writerow(row)

            if do_accumulate:
                results = accumulator.getResults()
                for i, individual in enumerate(result_sets[0].getPopulation()):
                    origin_id = individual.getStringData(self.oid)
                    writer.writerow([origin_id, results[i]])

        print 'results written to "{}"'.format(self.target_csv)


class OTPEvaluation(object):
    '''
    Use to calculate the reachability between origins and destinations with OpenTripPlanner
    and to save the results to a csv file

    Parameters
    ----------
    router: name of the router to use for trip planning
    print_every_n_lines: optional, determines how often progress in processing origins/destination is written to stdout (default: 50)
    calculate_details: optional, if True, evaluates additional informations about itineraries (a little slower)
    '''
    def __init__(self, graph_path, router, print_every_n_lines=50, calculate_details=False, smart_search=False):
        self.otp = OtpsEntryPoint.fromArgs([ "--graphs", graph_path, "--router", router])
        router = self.otp.getRouter()
        self.batch_processor = self.otp.createBatchProcessor(router)
        self.request = self.otp.createBatchRequest()
        self.request.setEvalItineraries(calculate_details)
        # smart search needs details (esp. start/arrival times),
        # even if not wanted explicitly
        if smart_search:
            calculate_details = True
        self.calculate_details = calculate_details
        self.smart_search = smart_search
        self.arrive_by = False
        self.print_every_n_lines = print_every_n_lines

    def setup(self,
              date_time=None, max_walk=None, walk_speed=None,
              bike_speed=None, clamp_wait=None, banned='', modes=None,
              arrive_by=False, max_transfers=None, max_pre_transit_time=None,
              wheel_chair_accessible=False, max_slope=None, n_threads=None):
        '''
        sets up the routing request

        Parameters
        ----------
        date_time: optional, datetime object, start respectively arrival time (if arriveby == True)
        modes: optional, string with comma-seperated traverse-modes to use
        banned: optional, string with comma-separated route specs, each of the format[agencyId]_[routeName]_[routeId]
        arrive_by: optional, if True, given time is arrival time (reverts search tree)
        max_walk: optional, maximum distance (in meters) the user is willing to walk
        walk_speed: optional, walking speed in m/s
        bike_speed: optional, bike speed in m/s
        clamp_wait: optional, maximum wait time in seconds the user is willing to delay trip start (-1 seems to mean it will be ignored)
        max_transfers: optional, maximum number of transfers (= boardings - 1)
        max_pre_transit_time: optional, maximum time in seconds of pre-transit travel when using drive-to-transit (park andride or kiss and ride)
        wheel_chair_accessible: optional, if True, the trip must be wheelchair accessible (defaults to False)
        max_slope: optional, maximum slope of streets for wheelchair trips
        n_threads: optional, number of threads to be used in evaluation
        '''

        if date_time is not None:
            self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second)

        self.request.setArriveBy(arrive_by)
        self.arrive_by = arrive_by
        self.request.setWheelchairAccessible(wheel_chair_accessible)
        if n_threads is not None:
            self.request.setThreads(n_threads)
        if max_walk is not None:
            self.request.setMaxWalkDistance(max_walk)
        if walk_speed is not None:
            self.request.setWalkSpeedMs(walk_speed)
        if bike_speed is not None:
            self.request.setBikeSpeedMs(bike_speed)
        if clamp_wait is not None:
            self.request.setClampInitialWait(clamp_wait)
        if banned:
            self.request.setBannedRoutes(banned)
        if max_slope is not None:
            self.request.setMaxSlope(max_slope)
        if max_transfers is not None:
            self.request.setMaxTransfers(max_transfers)
        if max_pre_transit_time is not None:
            self.request.setMaxPreTransitTime(max_pre_transit_time)

        if modes:
            if isinstance(modes, list):
                modes = ','.join(modes)
            self.request.setModes(modes)

    def evaluate(self, times, max_time, origins_csv, destinations_csv, csv_writer, split=500, do_merge=False):
        '''
        evaluate the shortest paths between origins and destinations
        uses the routing options set in setup() (run it first!)

        Parameters
        ----------
        times: list of date times, the desired start/arrival times for evaluation
        origins_csv: file with origin points
        destinations_csv: file with destination points
        csv_writer: CSVWriter, configured writer to write results
        do_merge: merge the results over time, only keeping the best connections
        max_time: maximum travel-time in seconds (the smaller this value, the smaller the shortest path tree, that has to be created; saves processing time)
        '''

        origins = self.otp.loadCSVPopulation(origins_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)
        destinations = self.otp.loadCSVPopulation(destinations_csv, LATITUDE_COLUMN, LONGITUDE_COLUMN)

        sources = origins if not self.arrive_by else destinations
        n_slices = (sources.size() / split) + 1

        if n_slices > 1:
            print 'Splitting sources into {} part(s) with {} points each part'.format(n_slices, split)

        from_index = 0;
        to_index = 0;
        i = 1

        while True:
            if to_index >= sources.size():
                break
            from_index = to_index
            to_index += split
            if to_index >= sources.size():
                to_index = sources.size()
            sliced_sources = sources.get_slice(from_index, to_index)
            if n_slices > 1:
                print('calculating part {}/{}'.format(i, n_slices))
            i += 1

            if not self.arrive_by:
                origins = sliced_sources
            else:
                destinations = sliced_sources
            self.request.setOrigins(origins)
            self.request.setDestinations(destinations)
            self.request.setLogProgress(self.print_every_n_lines)

            if self.arrive_by:
                time_note = ' arrival time '
            else:
                time_note = 'start time '

    #         # if evaluation is performed in a time window, routes exceeding the window will be ignored
    #         # (worstTime already takes care of this, but the time needed to reach the snapped the OSM point is also taken into account here)
    #         if len(times) > 1:
    #             print 'Cutoff set: routes with {}s exceeding the time window ({}) will be ignored (incl. time to reach OSM-net)'.format(time_note, times[-1])
    #             cutoff = times[-1]
    #             self.request.setCutoffTime(cutoff.year, cutoff.month, cutoff.day, cutoff.hour, cutoff.minute, cutoff.second)

            # iterate all times
            results = [] # dimension (if not merged): times x targets (origins resp. destinations)
            sdf = SimpleDateFormat('HH:mm:ss')
            sdf.setTimeZone(TimeZone.getTimeZone("GMT +2"))
            for t, date_time in enumerate(times):
                # compare seconds since epoch (different ways to get it from java/python date)
                epoch = datetime.utcfromtimestamp(0)
                time_since_epoch = (date_time - epoch).total_seconds()
                self.request.setDateTime(date_time.year, date_time.month, date_time.day, date_time.hour, date_time.minute, date_time.second)
                # has to be set every time after setting datetime (and also AFTER setting arriveby)
                self.request.setMaxTimeSec(max_time)

                msg = 'Starting evaluation of routes with ' + time_note + date_time.strftime(DATETIME_FORMAT)
                print msg

                results_dt = self.batch_processor.evaluate(self.request)

                # if there already was a calculation: merge it with new results
                if do_merge and len(results) > 0:
                    for i, prev_result in enumerate(results[0]):
                        if prev_result is not None:
                            prev_result.merge(results_dt[i])
                #write and append if no merging is needed (saves memory)
                else:
                    search_time = sdf.format(date_time)
                    csv_writer.write(results_dt, additional_columns={'search_time': search_time}, append=True)
                    for r in results_dt:
                        del(r)

            if do_merge:
                # flatten the results
                results = [r for res in results for r in res]
                csv_writer.write(results, append=False)



