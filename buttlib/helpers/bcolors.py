"""make strings pretty"""
class BColors:
    """class wrapper for colors and a formatting function"""
    def __init__(self):
        self.__colors = {
            "HEADER": '\033[95m',
            "OKBLUE": '\033[94m',
            "OKGREEN": '\033[92m',
            "WARNING": '\033[93m',
            "FAIL": '\033[91m',
            "ENDC": '\033[0m',
            "BOLD": '\033[1m',
            "UNDERLINE": '\033[4m',
            "BOLDBLUE": '\033[1m\033[94m'}

    def color_string(self, string_contents, level="OKBLUE"):
        """make strings pretty"
        :params string_contents: string to pretify
        :params level: color level
        :returns: string
        """
        return "{}{}{}".format(self.__colors[level], string_contents, self.__colors['ENDC'])

    def bcprint(self, string_contents, level="OKBLUE"):
        """make strings pretty"
        :params string_contents: string to pretify
        :params level: color level
        :returns: string
        """
        print("{}{}{}".format(self.__colors[level], string_contents, self.__colors['ENDC']))
