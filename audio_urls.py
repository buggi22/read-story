from bs4 import BeautifulSoup
import requests
import re
import sys
import argparse

from timeit import default_timer

def start_timer():
    start = default_timer()
    return lambda: default_timer() - start

batch_size_limit = 10

def get_audio_urls(words):
    '''
    Uses the MediaWiki API for Wiktionary to download batches of URLs
    corresponding to audio files containing US-English pronunciations of the
    given list of words

    See: https://www.mediawiki.org/wiki/API:Query
    '''
    result = dict()
    batches = [words[i:i+batch_size_limit]
        for i in xrange(0, len(words), batch_size_limit)]
    for b in batches:
        current_result = get_audio_urls_small_batch(b)
        result.update(current_result)
    return result

def get_audio_urls_small_batch(words):
    assert len(words) <= batch_size_limit, "Batch size is too large"

    # Get an audio filename for each word
    query_url = ("https://en.wiktionary.org/w/api.php"
        + "?format=xml&action=query&titles="
        + "|".join([requests.utils.quote(w.lower()) for w in words])
        + "&rvprop=content&prop=revisions&redirects=1")

    timer = start_timer()
    print "Querying {}".format(query_url)
    response_text = requests.get(query_url).text
    print "Received response: {} sec".format(timer())
    response = BeautifulSoup(response_text, "lxml")

    audio_files = dict()
    for page in response.find_all("page"):
        title = page["title"]
        rev = page.find("rev")
        if rev is not None:
            match = re.search(r'\{\{audio\|(.*\.ogg)\|Audio \(US\)', rev.string)
            if match:
                audio_files[title.lower()] = "File:" + match.group(1)

    print "Audio files: {}".format(audio_files)

    # Get a url for each audio file
    query_url = ("https://en.wiktionary.org/w/api.php"
        + "?format=xml&action=query&titles="
        + '|'.join(audio_files.values())
        + "&prop=imageinfo&iiprop=url")

    timer = start_timer()
    print "Querying {}".format(query_url)
    response_text = requests.get(query_url).text
    print "Received response: {} sec".format(timer())
    response = BeautifulSoup(response_text, "lxml")

    audio_urls = dict()
    for page in response.find_all("page"):
        title = page["title"]
        ii = page.find("ii")
        if ii is not None:
            audio_urls[title] = ii["url"]

    print "Audio urls: {}".format(audio_urls)

    # Build a mapping from words to urls
    words_to_urls = dict()
    for word in words:
        word = word.lower()
        if word in audio_files and audio_files[word] in audio_urls:
            words_to_urls[word] = audio_urls[audio_files[word]]

    return words_to_urls

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--words", default="The elephant walks")
    parser.add_argument("--output_file", default="example.html")
    args = parser.parse_args(sys.argv[1:])

    words = args.words.split()

    audio_urls = get_audio_urls(words)
    for w, u in audio_urls.items():
        print "{} -> {}".format(w, u)

    output_file = args.output_file
    print "Outputting to {}".format(output_file)

    doc = BeautifulSoup("<html><body></body></html>", "lxml")
    doc.body.append(doc.new_tag("script", src="js/playsound.js"))
    for i, w in enumerate(words):
        span = doc.new_tag("span",
            id="{}_{}".format(i, w.lower()), onclick="play(this);")
        span.string = w
        doc.body.append(span)

        url = audio_urls.get(w.lower())
        if url is not None:
            doc.body.append(doc.new_tag("audio",
                src=url, preload="auto", id=w.lower()+"_audio",
                type="audio/ogg"))

    with open(output_file, "w") as f:
        f.write(doc.prettify())
