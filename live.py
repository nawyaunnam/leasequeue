from feeds import fetch,run
from engine import Queue
import time
from collections import Counter

def acquire():
    source=fetch('https://api.github.com/events?per_page=100')
    source=dict(source,payload=[{key:event[key] for key in ('id','type','repo','created_at')} for event in source['payload']])
    return {'sources':[source]}


def analyze(snapshot):
    events=snapshot['sources'][0]['payload']
    q=Queue('live-queue.db')
    try:
        for event in events:
            q.submit(event['id'],{'type':event['type'],'repository':event['repo']['name']},time.time())
        counts=Counter()
        while True:
            job=q.claim(time.time())
            if job is None: break
            counts[job['payload']['type']]+=1
            q.ack(job['id'],job['token'],time.time())
        states=dict(q.db.execute('SELECT state,COUNT(*) FROM jobs GROUP BY state').fetchall())
        return {'project':'LeaseQueue','source_events':len(events),'processed_this_run':sum(counts.values()),
                'event_types':dict(counts),'durable_queue_states':states,
                'note':'Replays deduplicate by GitHub event ID; counts for already completed jobs are zero.'}
    finally:q.close()


if __name__=='__main__': run(acquire,analyze)
