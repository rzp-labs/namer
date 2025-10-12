"""
Reads movie.xml (your.movie.name.nfo) of Emby/Jellyfin format in to a LookedUpFileInfo,
allowing the metadata to be written in to video files (currently only mp4's),
or used in renaming the video file.
"""

from pathlib import Path
from typing import Optional, List, Union, Sequence, cast

from defusedxml.minidom import parseString  # type: ignore[import]  # Incomplete type stubs
from loguru import logger
# codacy-disable-next-line
from xml.dom.minidom import CharacterData, Document, Element, Node  # nosec B408: Using defusedxml for parsing, only importing types

from namer.configuration import NamerConfig
from namer.command import set_permissions
from namer.comparison_results import LookedUpFileInfo, Performer
from namer.videophash import PerceptualHash


NodeHost = Union[Document, Element]


def _first_element(nodes: Sequence[Node]) -> Optional[Element]:
    for candidate in nodes:
        if isinstance(candidate, Element):
            return candidate
    return None


def get_childnode(node: NodeHost, name: str) -> Optional[Element]:
    """Get child node, returns None if not found."""
    return _first_element(node.getElementsByTagName(name))


@logger.catch(reraise=True)
def require_childnode(node: NodeHost, name: str) -> Element:
    """
    Get child node, raises ValueError if not found.
    
    Use this for required XML elements that must be present.
    """
    element = get_childnode(node, name)
    if element is None:
        raise ValueError(f"Required XML element '{name}' not found")
    return element


def get_all_childnode(node: NodeHost, name: str) -> List[Element]:
    return [child for child in node.getElementsByTagName(name) if isinstance(child, Element)]


def _text_from_children(children: Sequence[Node]) -> Optional[str]:
    """Collect and concatenate text from all CharacterData nodes."""
    text_parts = []
    for child in children:
        if isinstance(child, CharacterData):
            text_parts.append(child.data)
    
    if not text_parts:
        return None
    
    return ''.join(text_parts)


def get_childnode_text(node: NodeHost, name: str) -> Optional[str]:
    element = get_childnode(node, name)
    if element is None:
        return None
    return _text_from_children(element.childNodes)


def get_all_childnode_text(node: NodeHost, name: str) -> List[str]:
    results: List[str] = []
    for element in get_all_childnode(node, name):
        text = _text_from_children(element.childNodes)
        if text is not None:
            results.append(text)
    return results


def parse_movie_xml_file(xml_file: Path) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    content = xml_file.read_text(encoding='UTF-8')

    movie: Document = cast(Document, parseString(bytes(content, encoding='UTF-8')))
    info = LookedUpFileInfo()
    
    # Require title element exists and validate it's not empty
    require_childnode(movie, 'title')  # Raises if missing
    title_text = get_childnode_text(movie, 'title')
    if not title_text or not title_text.strip():
        raise ValueError(f"XML file {xml_file} has empty or whitespace-only <title> element")
    info.name = title_text.strip()
    
    studios = get_all_childnode_text(movie, 'studio')
    info.site = studios[0] if studios else None
    info.date = get_childnode_text(movie, 'releasedate')
    info.description = get_childnode_text(movie, 'plot')
    art = get_childnode(movie, 'art')
    info.poster_url = get_childnode_text(art, 'poster') if art else None

    info.performers = []
    for actor in get_all_childnode(movie, 'actor'):
        name = get_childnode_text(actor, 'name')
        if name:
            performer = Performer(name)
            performer.alias = get_childnode_text(actor, 'alias')
            performer.role = get_childnode_text(actor, 'role')
            info.performers.append(performer)

    phoenixadulturlid = get_childnode_text(movie, 'phoenixadulturlid')
    if phoenixadulturlid:
        info.look_up_site_id = phoenixadulturlid

    theporndbid = get_childnode_text(movie, 'theporndbid')
    if theporndbid:
        info.uuid = theporndbid

    info.tags = []
    for genre in get_all_childnode_text(movie, 'genre'):
        info.tags.append(str(genre))

    info.original_parsed_filename = None
    info.original_query = None
    info.original_response = None

    return info


def add_sub_element(doc: Document, parent: Element, name: str, text: Optional[str] = None) -> Element:
    sub_element = doc.createElement(name)
    parent.appendChild(sub_element)

    if text:
        txt_node = doc.createTextNode(text)
        sub_element.appendChild(txt_node)

    return sub_element


def add_all_sub_element(doc: Document, parent: Element, name: str, text_list: List[str]) -> None:
    if text_list:
        for text in text_list:
            sub_element = doc.createElement(name)
            parent.appendChild(sub_element)
            txt_node = doc.createTextNode(text)
            sub_element.appendChild(txt_node)


def write_movie_xml_file(info: LookedUpFileInfo, config: NamerConfig, trailer: Optional[Path] = None, poster: Optional[Path] = None, background: Optional[Path] = None, phash: Optional[PerceptualHash] = None) -> str:
    """
    Parse porndb info and create an Emby/Jellyfin xml file from the data.
    """
    doc = Document()
    root: Element = doc.createElement('movie')
    doc.appendChild(root)
    add_sub_element(doc, root, 'plot', info.description)
    add_sub_element(doc, root, 'outline')
    add_sub_element(doc, root, 'title', info.name)
    add_sub_element(doc, root, 'dateadded')
    add_sub_element(doc, root, 'trailer', str(trailer) if trailer else info.trailer_url)
    add_sub_element(doc, root, 'year', info.date[:4] if info.date else None)
    add_sub_element(doc, root, 'premiered', info.date)
    add_sub_element(doc, root, 'releasedate', info.date)
    add_sub_element(doc, root, 'mpaa', 'XXX')

    art = add_sub_element(doc, root, 'art')
    add_sub_element(doc, art, 'poster', poster.name if poster else info.poster_url)
    add_sub_element(doc, art, 'background', background.name if background else info.background_url)

    if config.enable_metadataapi_genres:
        add_all_sub_element(doc, root, 'genre', info.tags)
    else:
        add_all_sub_element(doc, root, 'tag', info.tags)
        add_sub_element(doc, root, 'genre', config.default_genre)

    add_sub_element(doc, root, 'studio', info.site)
    add_sub_element(doc, root, 'theporndbid', str(info.uuid))
    add_sub_element(doc, root, 'theporndbguid', str(info.guid))
    add_sub_element(doc, root, 'phoenixadultid')
    add_sub_element(doc, root, 'phoenixadulturlid')

    add_sub_element(doc, root, 'phash', str(phash.phash) if phash else None)
    add_sub_element(doc, root, 'sourceid', info.source_url)

    for performer in info.performers:
        actor = add_sub_element(doc, root, 'actor')
        add_sub_element(doc, actor, 'type', 'Actor')
        add_sub_element(doc, actor, 'name', performer.name)
        add_sub_element(doc, actor, 'alias', performer.alias)
        add_sub_element(doc, actor, 'role', performer.role)

        if performer.image:
            image = performer.image.name if isinstance(performer.image, Path) else performer.image
            add_sub_element(doc, actor, 'image', image)

        add_sub_element(doc, actor, 'thumb')

    add_sub_element(doc, root, 'fileinfo')

    return str(doc.toprettyxml(indent='  ', newl='\n', encoding='UTF-8'), encoding='UTF-8')


def write_nfo(video_file: Path, new_metadata: LookedUpFileInfo, namer_config: NamerConfig, trailer: Optional[Path], poster: Optional[Path], background: Optional[Path], phash: Optional[PerceptualHash]):
    """
    Writes an .nfo to the correct place for a video file.
    """
    if video_file and new_metadata and namer_config.write_nfo:
        target = video_file.parent / (video_file.stem + '.nfo')
        with open(target, 'wt', encoding='UTF-8') as nfo_file:
            data = write_movie_xml_file(new_metadata, namer_config, trailer, poster, background, phash)
            nfo_file.write(data)

        set_permissions(target, namer_config)
