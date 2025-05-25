class MetricsCollector:
    """
    Compute per-run summaries and aggregated averages for: 
        - journey metrics 
        - TLS interactions 
        - max-speed
        - sudden braking
        - lane changes
        - collisions
        - total wait time
    """

    def summarise_run(self, run_data: dict, route_index: int) -> list[list]:
        """
        Per-run row:
        [Agent, Route, Time, Distance, AvgSpeed, MaxSpeed,
         Edges, TLS_enc, Amber_enc, Red_enc, Amber_runs, Red_runs,
         Sudden_brakes, MaxDecel, AvgDecel, Lane_changes, Collisions,
         WaitTime(s)]
        """
        rows = []
        for vid, rec in run_data.items():
            if rec['end_step'] is not None:
                t = rec['end_step']
                avg_sp = rec['total_distance'] / t if t > 0 else 0.0
                avg_decel = (
                    rec['sum_decel'] / rec['sudden_brake_count']
                    if rec['sudden_brake_count'] > 0 else 0.0
                )

                rows.append([
                    vid,
                    route_index,
                    t,
                    round(rec['total_distance'], 2),
                    round(avg_sp, 2),
                    round(rec['max_speed'], 2),
                    len(rec['edges_visited']),
                    len(rec['tls_encountered']),  
                    rec['amber_encountered'],
                    rec['red_encountered'],
                    rec['green_encountered'],
                    rec['amber_run_count'],
                    rec['red_run_count'],
                    rec['green_run_count'],
                    rec['sudden_brake_count'],
                    round(rec['max_decel'], 2),
                    round(avg_decel, 2),
                    rec['lane_change_count'],
                    rec.get('collision_count', 0),
                    round(rec.get('wait_time', 0.0), 2)
                ])
            else:
                # placeholders for 18 columns
                rows.append([vid, route_index] + ["-"] * 17)
        return rows

    def compute_averages(self, all_runs: list[tuple[dict, int]]) -> list[list]:
        """
        Averages row:
        [Agent, AvgTime, AvgDist, AvgSpeed, AvgMaxSpeed,
        AvgEdges, NumRuns, AvgTLS_enc, AvgAmber_enc, AvgRed_enc,
        AvgAmber_runs, AvgRed_runs, AvgSudden_brakes, AvgMaxDecel,
        AvgAvgDecel, AvgLane_changes, AvgCollisions, AvgWaitTime(s),
        TotalTLS_enc, TotalAmber_enc, TotalRed_enc]
        """

        # init accumulators for metrics
        agg = {
            vid: {
                'sum_time': 0, 'sum_dist': 0.0, 'sum_sp': 0.0, 'sum_max_sp': 0.0,
                'sum_edges': 0, 'sum_tls': 0, 'sum_amb_enc': 0, 'sum_red_enc': 0, 'sum_green_enc': 0,
                'sum_amb_runs': 0, 'sum_red_runs': 0, 'sum_green_runs':0, 'sum_sud_brakes': 0, 'sum_max_decel': 0.0, 
                'sum_avg_decel': 0.0, 'sum_lane_changes': 0, 'sum_collisions': 0, 'sum_wait_time': 0.0, 'count': 0
            }
            for vid in ["safe_1", "risky_1"]
        }

        # acc all successful runs
        for run_data, _ in all_runs:
            for vid, rec in run_data.items():
                if rec.get('end_step') is None:
                    continue
                s = agg[vid]
                t = rec['end_step']
                avg_decel = (
                    rec['sum_decel'] / rec['sudden_brake_count']
                    if rec['sudden_brake_count'] > 0 else 0.0
                )

                s['sum_time'] += t
                s['sum_dist'] += rec['total_distance']
                s['sum_sp'] += (rec['total_distance'] / t if t > 0 else 0.0)
                s['sum_max_sp'] += rec.get('max_speed', 0.0)
                s['sum_edges'] += len(rec['edges_visited'])
                s['sum_tls'] += len(rec['tls_encountered'])
                s['sum_amb_enc'] += rec['amber_encountered']
                s['sum_red_enc'] += rec['red_encountered']
                s['sum_green_enc'] += rec['green_encountered']
                s['sum_amb_runs'] += rec['amber_run_count']
                s['sum_red_runs'] += rec['red_run_count']
                s['sum_green_runs'] += rec['green_run_count']
                s['sum_sud_brakes'] += rec['sudden_brake_count']
                s['sum_max_decel'] += rec['max_decel']
                s['sum_avg_decel'] += avg_decel
                s['sum_lane_changes'] += rec['lane_change_count']
                s['sum_collisions'] += rec.get('collision_count', 0)
                s['sum_wait_time'] += rec.get('wait_time', 0.0)
                s['count'] += 1

        # compute averages
        rows = []
        for vid, s in agg.items():
            c = s['count']
            if c > 0:
                rows.append([
                    vid,
                    round(s['sum_time'] / c, 2),
                    round(s['sum_dist'] / c, 2),
                    round(s['sum_sp'] / c, 2),
                    round(s['sum_max_sp'] / c, 2),
                    round(s['sum_edges'] / c, 2),
                    c,
                    round(s['sum_tls'] / c, 2),
                    round(s['sum_amb_enc'] / c, 2),
                    round(s['sum_red_enc'] / c, 2),
                    round(s['sum_green_enc'] /c, 2),
                    round(s['sum_amb_runs'] / c, 2),
                    round(s['sum_red_runs'] / c, 2),
                    round(s['sum_green_runs'] / c, 2),
                    round(s['sum_sud_brakes'] / c, 2),
                    round(s['sum_max_decel'] / c, 2),
                    round(s['sum_avg_decel'] / c, 2),
                    round(s['sum_lane_changes'] / c, 2),
                    round(s['sum_collisions'] / c, 2),
                    round(s['sum_wait_time'] / c, 2),
                    s['sum_tls'],
                    s['sum_amb_enc'],
                    s['sum_red_enc']
                ])
            else:
                rows.append([vid] + ["N/A"] * 21)
        return rows
