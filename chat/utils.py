import re

def extract_links(text):
    """Extracts HTTP and HTTPS links from a given text string.

    Args:
        text: The input string to search for links.

    Returns:
        A list of strings, where each string is an extracted link.
        Returns an empty list if no links are found.
    """
    regex = r"(https?://\S+)"
    links = re.findall(regex, text)
    return links

def get_key_if_not_empty(kvdict):
  """
  Returns a key from the dictionary if it's not empty, otherwise returns None.
  If the dictionary has multiple keys, it returns the first key encountered.
  """
  if kvdict:
    return next(iter(kvdict))
  else:
    return None