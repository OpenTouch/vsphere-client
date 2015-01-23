from datetime import timedelta, datetime
from pyVmomi import vim

class EsxPerfCounter:
    def __init__(self, service):
        self.content = service.RetrieveContent()
        self.pm = self.content.perfManager
        self.vchtime = service.CurrentTime()

        # Get all the performance counters
        self.counters = {}
        for c in self.pm.perfCounter:
            cid = "{}.{}.{}".format(c.groupInfo.key, c.nameInfo.key, c.rollupType)
            self.counters[cid] = c.key

    def show_counters(self):
        array = []
        for c in self.counters:
            array.append([self.counters[c], c])
        array.sort()
        for a in array:
            print a[0], a[1]

    def counter_id(self, name):
        return self.counters[name]

    def get(self, name, instance, entity, interval):
        cid = self.counter_id(name)
        mid = vim.PerformanceManager.MetricId(counterId=cid, instance=instance)
        start = self.vchtime - timedelta(minutes=(interval + 1))
        end = self.vchtime - timedelta(minutes=1)
        query = vim.PerformanceManager.QuerySpec(intervalId=20, entity=entity, metricId=[mid], startTime=start, endTime=end)
        r = self.pm.QueryPerf(querySpec=[query])
        if r:
            values = r[0].value[0].value
            samples = len(r[0].sampleInfo)
            total = float(sum(values))
            mean = total / samples
            return values, samples, total, mean
        else:
            print 'ERROR: Performance results empty.'
            print 'Troubleshooting info:'
            print 'vCenter/host date and time: {}'.format(self.vchtime)
            print 'Start perf counter time   :  {}'.format(start)
            print 'End perf counter time     :  {}'.format(end)
            print(query)
            return None
