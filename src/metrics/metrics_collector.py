# metrics_collector.py

class MetricsCollector:
    """
    Compute per-run summaries and aggregated averages
    for journey metrics, TLS interactions, max-speed, sudden braking, and collisions.
    """

    def summarise_run(self, run_data: dict, route_index: int) -> list[list]:
        """
        Per-run row:
        [Agent,Route,Time,Distance,AvgSpeed,MaxSpeed,
         Edges,TLS_enc,TLS_stops,TLS_wait,
         Amber_enc,Red_enc,Amber_runs,Red_runs,
         Sudden_brakes,MaxDecel,AvgDecel,
         AvgWaitTL,Collisions]
        """
        rows = []
        for vid, rec in run_data.items():
            if rec['end_step'] is not None:
                t = rec['end_step']
                avg_sp = rec['total_distance'] / t if t>0 else 0.0
                # average decel per brake
                avg_decel = (rec['sum_decel'] / rec['sudden_brake_count']
                             if rec['sudden_brake_count']>0 else 0.0)
                avg_wait_tl = self.get_avg_waiting_time(rec)

                rows.append([
                    vid,
                    route_index,
                    t,
                    round(rec['total_distance'],2),
                    round(avg_sp,2),
                    round(rec['max_speed'],2),
                    len(rec['edges_visited']),
                    len(rec['tls_encountered']),
                    rec['tls_stop_count'],
                    round(rec['tls_wait_time'],2),
                    rec['amber_encountered'],
                    rec['red_encountered'],
                    rec['amber_run_count'],
                    rec['red_run_count'],
                    rec['sudden_brake_count'],
                    round(rec['max_decel'],2),
                    round(avg_decel,2),
                    round(avg_wait_tl,2),
                    rec.get('collision_count',0)
                ])
            else:
                # placeholders for 19 columns
                rows.append([vid, route_index] + ["-"] * 17)
        return rows

    def compute_averages(self, all_runs: list[tuple[dict,int]]) -> list[list]:
        """
        Aggregated averages row:
        [Agent,AvgTime,AvgDist,AvgSpeed,AvgMaxSpeed,
         AvgEdges,NumRuns,AvgTLS_enc,AvgTLS_stops,AvgTLS_wait,
         AvgAmber_enc,AvgRed_enc,AvgAmber_runs,AvgRed_runs,
         AvgSudden_brakes,AvgMaxDecel,AvgAvgDecel,
         AvgWaitTL,AvgCollisions]
        """
        agg = {
            vid: {
                'sum_time':0,'sum_dist':0.0,'sum_sp':0.0,'sum_max_sp':0.0,
                'sum_edges':0,'sum_tls':0,'sum_stops':0,'sum_wait':0.0,
                'sum_amb_enc':0,'sum_red_enc':0,'sum_amb_runs':0,'sum_red_runs':0,
                'sum_sud_brakes':0,'sum_max_decel':0.0,'sum_avg_decel':0.0,
                'sum_wait_tl':0.0,'sum_collisions':0,'count':0
            } for vid in ["safe_1","risky_1"]
        }

        for run_data, _ in all_runs:
            for vid, rec in run_data.items():
                if rec.get('end_step') is None:
                    continue
                stats = agg[vid]
                t = rec['end_step']
                stats['sum_time']       += t
                stats['sum_dist']       += rec['total_distance']
                stats['sum_sp']         += (rec['total_distance']/t if t>0 else 0.0)
                stats['sum_max_sp']     += rec.get('max_speed',0.0)
                stats['sum_edges']      += len(rec['edges_visited'])
                stats['sum_tls']        += len(rec['tls_encountered'])
                stats['sum_stops']      += rec['tls_stop_count']
                stats['sum_wait']       += rec['tls_wait_time']
                stats['sum_amb_enc']    += rec['amber_encountered']
                stats['sum_red_enc']    += rec['red_encountered']
                stats['sum_amb_runs']   += rec['amber_run_count']
                stats['sum_red_runs']   += rec['red_run_count']
                stats['sum_sud_brakes'] += rec['sudden_brake_count']
                stats['sum_max_decel']  += rec['max_decel']
                # per-run avg decel
                avg_decel = (rec['sum_decel']/rec['sudden_brake_count']
                             if rec['sudden_brake_count']>0 else 0.0)
                stats['sum_avg_decel']  += avg_decel
                stats['sum_wait_tl']    += self.get_avg_waiting_time(rec)
                stats['sum_collisions'] += rec.get('collision_count',0)
                stats['count']          += 1

        rows = []
        for vid, s in agg.items():
            c = s['count']
            if c>0:
                rows.append([
                    vid,
                    round(s['sum_time']/c,2),
                    round(s['sum_dist']/c,2),
                    round(s['sum_sp']/c,2),
                    round(s['sum_max_sp']/c,2),
                    round(s['sum_edges']/c,2),
                    c,
                    round(s['sum_tls']/c,2),
                    round(s['sum_stops']/c,2),
                    round(s['sum_wait']/c,2),
                    round(s['sum_amb_enc']/c,2),
                    round(s['sum_red_enc']/c,2),
                    round(s['sum_amb_runs']/c,2),
                    round(s['sum_red_runs']/c,2),
                    round(s['sum_sud_brakes']/c,2),
                    round(s['sum_max_decel']/c,2),
                    round(s['sum_avg_decel']/c,2),
                    round(s['sum_wait_tl']/c,2),
                    round(s['sum_collisions']/c,2),
                ])
            else:
                rows.append([vid] + ["N/A"] * 18)
        return rows

    @staticmethod
    def get_avg_waiting_time(rec: dict) -> float:
        encountered = len(rec.get('tls_encountered', []))
        return rec.get('tls_wait_time',0.0)/encountered if encountered>0 else 0.0
