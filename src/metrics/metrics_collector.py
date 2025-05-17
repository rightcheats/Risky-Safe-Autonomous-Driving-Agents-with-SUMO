class MetricsCollector:
    """
    Compute per-run summaries and aggregated averages
    for journey metrics, traffic-light interactions, and collision counts.
    """

    def summarise_run(self, run_data: dict, route_index: int) -> list[list]:
        """
        Generate per-vehicle summary for a single simulation run.

        Each row contains:
        [Agent, Route, Time(steps), Distance(m), Speed(m/s), Edges,
         TLS_enc, TLS_stops, TLS_wait(s), Amber_enc, AvgWaitTL, Collisions]
        """
        rows: list[list] = []

        for vid, rec in run_data.items():
            if rec['end_step'] is not None:
                t = rec['end_step']
                avg_sp = rec['total_distance'] / t if t > 0 else 0.0
                avg_wait_tl = self.get_avg_waiting_time(rec)

                rows.append([
                    vid,
                    route_index,
                    t,
                    round(rec['total_distance'], 2),
                    round(avg_sp, 2),
                    len(rec['edges_visited']),
                    len(rec['tls_encountered']),
                    rec['tls_stop_count'],
                    round(rec['tls_wait_time'], 2),
                    rec['amber_encountered'],
                    round(avg_wait_tl, 2),
                    rec.get('collision_count', 0)
                ])
            else:
                # Agent did not reach its destination within max steps
                # Fill remaining columns with placeholders
                rows.append([vid, route_index] + ["-"] * 10)

        return rows

    def compute_averages(self, all_runs: list[tuple[dict, int]]) -> list[list]:
        """
        Compute aggregated averages across multiple runs.

        Each row contains:
        [Agent, AvgTime(steps), AvgDistance(m), AvgSpeed(m/s), AvgEdges,
         NumRuns, AvgTLS_enc, AvgTLS_stops, AvgTLS_wait(s), AvgAmber_enc,
         AvgWaitTL, AvgCollisions]
        """
        # Initialize accumulator for each vehicle
        agg = {
            vid: {
                'sum_time': 0,
                'sum_dist': 0.0,
                'sum_sp': 0.0,
                'sum_edges': 0,
                'sum_tls': 0,
                'sum_stops': 0,
                'sum_wait': 0.0,
                'sum_amb': 0,
                'sum_wait_tl': 0.0,
                'sum_collisions': 0,
                'count': 0
            }
            for vid in ["safe_1", "risky_1"]
        }

        # Accumulate metrics from each run
        for run_data, _ in all_runs:
            for vid, rec in run_data.items():
                if rec.get('end_step') is None:
                    continue

                stats = agg[vid]
                t = rec['end_step']
                stats['sum_time'] += t
                stats['sum_dist'] += rec['total_distance']
                stats['sum_sp'] += (rec['total_distance'] / t) if t > 0 else 0.0
                stats['sum_edges'] += len(rec['edges_visited'])
                stats['sum_tls'] += len(rec['tls_encountered'])
                stats['sum_stops'] += rec['tls_stop_count']
                stats['sum_wait'] += rec['tls_wait_time']
                stats['sum_amb'] += rec['amber_encountered']
                stats['sum_wait_tl'] += self.get_avg_waiting_time(rec)
                stats['sum_collisions'] += rec.get('collision_count', 0)
                stats['count'] += 1

        # Build averaged rows
        rows: list[list] = []
        for vid, stats in agg.items():
            c = stats['count']
            if c > 0:
                rows.append([
                    vid,
                    round(stats['sum_time']   / c, 2),
                    round(stats['sum_dist']   / c, 2),
                    round(stats['sum_sp']     / c, 2),
                    round(stats['sum_edges']  / c, 2),
                    c,
                    round(stats['sum_tls']    / c, 2),
                    round(stats['sum_stops']  / c, 2),
                    round(stats['sum_wait']   / c, 2),
                    round(stats['sum_amb']    / c, 2),
                    round(stats['sum_wait_tl'] / c, 2),
                    round(stats['sum_collisions'] / c, 2)
                ])
            else:
                # No successful runs for this agent
                rows.append([vid] + ["N/A"] * 11)

        return rows

    @staticmethod
    def get_avg_waiting_time(rec: dict) -> float:
        """
        Calculate the average waiting time at traffic lights for a vehicle.
        If the vehicle never encountered any TLS, returns 0.
        """
        encountered = len(rec.get('tls_encountered', []))
        return rec.get('tls_wait_time', 0.0) / encountered if encountered > 0 else 0.0