from collections import defaultdict

class Tablerenderer:
    def __init__(self, header = [], columnwidth = 10):
        self.data = defaultdict(list, { x:[] for x in header })
        self.columnwidth = columnwidth

    def render(self):
        header = []
        for column in self.data.keys():
            header.append(column.rjust(self.columnwidth))
        separator = ['-'*self.columnwidth]*len(self.data)
        lines = ['|'.join(header), '|'.join(separator)]
        i = 0
        while True:
            data_available = False
            line = []
            for column in self.data.values():
                try:
                    line.append(column[i].rjust(self.columnwidth))
                    data_available = True
                except IndexError:
                    line.append(' '*self.columnwidth)
            if data_available:
                i += 1
                lines.append('|'.join(line))
            else:
                break
        return '\n'.join(lines)
            

