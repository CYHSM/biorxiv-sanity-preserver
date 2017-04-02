from contextlib import contextmanager

import os
import re
import pickle
import tempfile

# global settings
# -----------------------------------------------------------------------------
class Config(object):
    # main paper information repo file
    db_path = 'db.p'
    # intermediate processing folders
    pdf_dir = os.path.join('data', 'pdf')
    txt_dir = os.path.join('data', 'txt')
    thumbs_dir = os.path.join('static', 'thumbs')
    # intermediate pickles
    tfidf_path = 'tfidf.p'
    meta_path = 'tfidf_meta.p'
    sim_path = 'sim_dict.p'
    user_sim_path = 'user_sim.p'
    # sql database file
    db_serve_path = 'db2.p' # an enriched db.p with various preprocessing info
    database_path = 'as.db'
    serve_cache_path = 'serve_cache.p'
    
    banned_path = 'banned.txt' # for twitter users who are banned
    tmp_dir = 'tmp'

# Context managers for atomic writes courtesy of
# http://stackoverflow.com/questions/2333872/atomic-writing-to-file-with-python
@contextmanager
def _tempfile(*args, **kws):
    """ Context for temporary file.

    Will find a free temporary filename upon entering
    and will try to delete the file on leaving

    Parameters
    ----------
    suffix : string
        optional file suffix
    """

    fd, name = tempfile.mkstemp(*args, **kws)
    os.close(fd)
    try:
        yield name
    finally:
        try:
            os.remove(name)
        except OSError as e:
            if e.errno == 2:
                pass
            else:
                raise e


@contextmanager
def open_atomic(filepath, *args, **kwargs):
    """ Open temporary file object that atomically moves to destination upon
    exiting.

    Allows reading and writing to and from the same filename.

    Parameters
    ----------
    filepath : string
        the file path to be opened
    fsync : bool
        whether to force write the file to disk
    kwargs : mixed
        Any valid keyword arguments for :code:`open`
    """
    fsync = kwargs.pop('fsync', False)

    with _tempfile(dir=os.path.dirname(filepath)) as tmppath:
        with open(tmppath, *args, **kwargs) as f:
            yield f
            if fsync:
                f.flush()
                os.fsync(file.fileno())
        os.rename(tmppath, filepath)

def safe_pickle_dump(obj, fname):
    with open_atomic(fname, 'wb') as f:
        pickle.dump(obj, f, -1)


# arxiv utils
# -----------------------------------------------------------------------------

def strip_version(idstr):
    """ identity function if arxiv id has no version, otherwise strips it. """
    parts = idstr.split('v')
    return parts[0]

# "1511.08198v1" is an example of a valid arxiv id that we accept
def isvalidid(pid):
  return re.match('^\d+(v\d+)?$', pid)


def parse_biorxiv_url(url):
  """
  examples:

  http://biorxiv.org/content/early/2017/03/24/120444?rss=1
  http://biorxiv.org/content/early/2017/03/24/120444
  http://biorxiv.org/cgi/content/short/121814v1

  we want to extract the raw id and the version
  """
  if not 'biorxiv.org/' in url: return None, None

  #strip off ?rss=1 if it exists
  url = url[:url.find('?') if '?' in url else None]
  ix = url.rfind('/')
  idversion = url[ix+1:] # extract just the id (and the version)
  parts = idversion.split('v')
  if len(parts) > 2:
      print('error parsing url ' + url)
      return None, None
  if len(parts) == 1:
    return parts[0], None
  else:
    try:
      return parts[0], int(parts[1])
    except ValueError:
      return parts[0], None

def biorxiv_hacks(entry, cat):

  # add pdf link
  norss = lambda x: x[:x.rfind('?') if '?' in x else None]
  entry['link'] = norss(entry['link'])
  entry['links'].append({'type': 'application/pdf', 'href': entry['link']+'.full',
      'rel': 'alternate'})
  for i, link in enumerate(entry['links']):
      entry['links'][i]['href'] = norss(link['href'])

  # add published date
  entry['published'] = entry['prism_publicationdate']
  entry['arxiv_primary_category'] = {'term':cat}

  # add tags
  entry['tags'] = [{'term': cat}]

  # remove empty author entries
  entry['authors'] = [x for x in entry['authors'] if x]

  return entry


biorxiv_categories = ['Animal Behavior and Cognition',
              'Biochemistry',
              'Bioengineering',
              'Bioinformatics',
              'Biophysics',
              'Cancer Biology',
              'Cell Biology',
              'Clinical Trials',
              'Developmental Biology',
              'Ecology',
              'Epidemiology',
              'Evolutionary Biology',
              'Evolutionary Biology',
              'Genetics',
              'Genomics',
              'Immunology',
              'Microbiology',
              'Molecular Biology',
              'Neuroscience',
              'Paleontology',
              'Pathology',
              'Pharmacology and Toxicology',
              'Physiology',
              'Plant Biology',
              'Scientific Communication and Education',
              'Synthetic Biology',
              'Systems Biology',
              'Zoology'
             ]
