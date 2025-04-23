class MetricsCollector:
    """
    Compute per-run summaries and aggregated averages
    for journey and traffic-light metrics.
    """
    def summarise_run(self, run_data: dict, route_index: int) -> list[list]:
        rows = []
        for vid, rec in run_data.items():
            if rec['end_step'] is not None:
                t = rec['end_step']
                avg_sp = rec['total_distance'] / t if t > 0 else 0
                # Get the waiting time using the getWaitingTime method
                avg_wait_tl = self.get_avg_waiting_time(vid, rec)
                rows.append([
                    vid, route_index,
                    t,
                    round(rec['total_distance'], 2),
                    round(avg_sp, 2),
                    len(rec['edges_visited']),
                    len(rec['tls_encountered']),
                    rec['tls_stop_count'],
                    round(rec['tls_wait_time'], 2),
                    rec['amber_encountered'],
                    round(avg_wait_tl, 2)  # AvgWaitTL column added here
                ])
            else:
                # Agent didn’t reach destination
                rows.append([vid, route_index] + ["-"] * 9)
        return rows

    def compute_averages(self, all_runs: list[tuple[dict,int]]) -> list[list]:
        # Initialize aggregates
        agg = {vid: {
                    'sum_time':0,'sum_dist':0,'sum_sp':0,'sum_edges':0,
                    'sum_tls':0,'sum_stops':0,'sum_wait':0,'sum_amb':0,'count':0,'sum_wait_tl':0
               } for vid in ["safe_1","risky_1"]}

        # Accumulate
        for run_data, _ in all_runs:
            for vid, rec in run_data.items():
                stats = agg[vid]
                if rec['end_step'] is not None:
                    t = rec['end_step']
                    stats['sum_time']   += t
                    stats['sum_dist']   += rec['total_distance']
                    stats['sum_sp']     += rec['total_distance']/t if t > 0 else 0
                    stats['sum_edges']  += len(rec['edges_visited'])
                    stats['sum_tls']    += len(rec['tls_encountered'])
                    stats['sum_stops']  += rec['tls_stop_count']
                    stats['sum_wait']   += rec['tls_wait_time']
                    stats['sum_amb']    += rec['amber_encountered']
                    # Accumulate the waiting time for traffic lights
                    stats['sum_wait_tl'] += self.get_avg_waiting_time(vid, rec)
                    stats['count']      += 1

        # Build average rows
        rows = []
        for vid, stats in agg.items():
            c = stats['count']
            if c > 0:
                rows.append([
                    vid,
                    round(stats['sum_time']/c, 2),
                    round(stats['sum_dist']/c, 2),
                    round(stats['sum_sp']/c, 2),
                    round(stats['sum_edges']/c, 2),
                    c,
                    round(stats['sum_tls']/c, 2),
                    round(stats['sum_stops']/c, 2),
                    round(stats['sum_wait']/c, 2),
                    round(stats['sum_amb']/c, 2),
                    round(stats['sum_wait_tl']/c, 2)  # AvgWaitTL averaged and added here
                ])
            else:
                rows.append([vid] + ["N/A"] * 10)
        return rows

    def get_avg_waiting_time(self, vid: str, rec: dict) -> float:
        """
        Calculate the average waiting time for traffic lights for the given vehicle.
        Assumes 'tls_wait_time' is available in the record.
        """
        return rec['tls_wait_time'] / len(rec['tls_encountered']) if rec['tls_encountered'] else 0
