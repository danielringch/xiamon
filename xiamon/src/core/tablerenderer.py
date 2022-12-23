from collections import defaultdict

class Tablerenderer:
    def __init__(self, header = []):
        self.data = defaultdict(list, { x:[] for x in header })

    def reverse(self):
        rows = max(len(x) for x in self.data.values())
        for column in self.data.values():
            for _ in range(len(column), rows):
                column.append('')
        for key in self.data.keys():
            self.data[key] = list(reversed(self.data[key]))

    def render(self):
        for column in self.data.values():
            for i in range(len(column)):
                column[i] = column[i] if isinstance(column[i], str) else str(column[i])

        widths = {x: len(x) for x in self.data.keys()}
        for key, value in self.data.items():
            if len(value) == 0:
                continue
            widths[key] = max(widths[key], max(len(x) for x in value)) + 1

        header = [x.rjust(widths[x]) for x in self.data.keys()]
        separator = ['-'*widths[x] for x in self.data.keys()]
        lines = ['|'.join(header), '|'.join(separator)]

        i = 0
        while True:
            data_available = False
            line = []
            for key, column in self.data.items():
                try:
                    line.append(column[i].rjust(widths[key]))
                    data_available = True
                except IndexError:
                    line.append(' '*widths[key])
            if data_available:
                i += 1
                lines.append('|'.join(line))
            else:
                break
        return '\n'.join(lines)
            

