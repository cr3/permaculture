"""La Société des Plantes database."""

import re
from collections.abc import Callable
from functools import partial
from typing import ClassVar

from attrs import define, evolve, field
from bs4 import BeautifulSoup
from defusedxml.ElementTree import fromstring

from permaculture.converter import Converter
from permaculture.http import HTTPSession
from permaculture.ingestor import logged_fetch
from permaculture.locales import Locales
from permaculture.nlp import normalize
from permaculture.plant import IngestorPlant
from permaculture.priority import LocationPriority, Priority

SDP_ORIGIN = "https://www.lasocietedesplantes.com"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

NON_PLANT_SLUGS = re.compile(
    r"kit-|certificat-|livre-|affiche-|t-shirt-|sweatshirt-"
    r"|atelier-|zine-|hydrolat|visite|rituel-|poivre-d"
    r"|camomille-allemande-sechee|basilic-sacre-rama-seche"
    r"|feuilles-de-framboisier-sechees|melisse-sechee"
    r"|sweatshirt-"
)



@define(frozen=True)
class SDPWeb:
    """La Société des Plantes web interface."""

    session: HTTPSession = field(factory=partial(HTTPSession, SDP_ORIGIN))

    def with_cache(self, storage):
        session = self.session.with_cache(storage)
        return evolve(self, session=session)

    def product_sitemap(self):
        """Fetch the product sitemap XML."""
        response = self.session.get("/product-sitemap.xml")
        return response.text

    def product_page(self, path):
        """Fetch an individual product page."""
        response = self.session.get(path)
        return response.text

    def source_url(self, path):
        """Return the full URL for a product page."""
        return f"{self.session.origin}{path}"


def parse_sitemap_urls(xml_text):
    """Extract French product paths from the sitemap XML.

    >>> urls = parse_sitemap_urls(
    ...     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ...     '<url><loc>https://www.lasocietedesplantes.com/produits/a/</loc></url>'
    ...     '</urlset>'
    ... )
    >>> urls
    ['/produits/a/']
    """
    root = fromstring(xml_text)
    urls = []
    for url_el in root.findall(f"{{{SITEMAP_NS}}}url"):
        loc = url_el.findtext(f"{{{SITEMAP_NS}}}loc", "")
        if "/produits/" in loc:
            path = loc.removeprefix(SDP_ORIGIN)
            slug = path.removeprefix("/produits/").rstrip("/")
            if not NON_PLANT_SLUGS.search(slug):
                urls.append(path)
    return urls


def parse_scientific_name(text):
    r"""Extract scientific name from a product description line.

    The first line typically looks like: "Withania somnifera, Solanacées"

    >>> parse_scientific_name("Withania somnifera, Solanacées")
    'withania somnifera'
    >>> parse_scientific_name("Borago officinalis alba, Boraginacées")
    'borago officinalis alba'
    >>> parse_scientific_name("No match here")
    """
    m = re.match(
        r"([A-Z][a-z]+ [a-z]+(?:\s+(?:var\.|subsp\.)\s+[a-z]+|\s+[a-z]+)*)"
        r"\s*,",
        text.strip(),
    )
    if m:
        return normalize(m.group(1))
    return None


def parse_family(text):
    r"""Extract the plant family from a description line.

    >>> parse_family("Withania somnifera, Solanacées")
    'solanacées'
    >>> parse_family("No match here")
    """
    m = re.match(
        r"[A-Z][a-z]+ [a-z].*,\s*([A-ZÀ-Ý][a-zà-ÿ]+(?:cées|acées))",
        text.strip(),
    )
    if m:
        return m.group(1).lower()
    return None


def parse_product(html):
    """Parse a product page and return a dict of raw fields.

    Returns None for pages that don't look like plant products.
    """
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h1", class_="product_title")
    if not title_el:
        return None

    common_name_fr = title_el.get_text(strip=True)

    # The short description contains the scientific name and family.
    short_el = soup.select_one(
        ".woocommerce-product-details__short-description"
    )
    short_text = short_el.get_text("\n", strip=True) if short_el else ""

    # Try to extract scientific name and family from short description.
    scientific_name = None
    family = None
    for line in short_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if scientific_name is None:
            scientific_name = parse_scientific_name(line)
            family = parse_family(line)
            if scientific_name:
                break

    # The full description lives in the tab-description panel.
    tab_el = soup.find(id="tab-description")
    description = tab_el.get_text("\n", strip=True) if tab_el else ""

    return {
        "common name": common_name_fr,
        "scientific name": scientific_name,
        "family": family,
        "description": description,
    }


@define(frozen=True)
class SDPConverter(Converter):
    """Converter for La Société des Plantes fields."""

    locales: Locales = field(factory=partial(Locales.from_domain, "sdp", language="fr"))

    DISPATCH: ClassVar[dict[str, Callable]] = {
        "common name": Converter.convert_ignore,
        "description": Converter.convert_string,
        "family": Converter.convert_string,
        "scientific name": Converter.convert_ignore,
    }


@define(frozen=True)
class SDPModel:
    """La Société des Plantes model."""

    web: SDPWeb = field(factory=SDPWeb)
    converter: SDPConverter = field(factory=SDPConverter)

    def with_cache(self, storage):
        web = self.web.with_cache(storage)
        return evolve(self, web=web)

    def product_paths(self):
        """Return all French product paths from the sitemap."""
        xml_text = self.web.product_sitemap()
        return parse_sitemap_urls(xml_text)

    def get_plant(self, path):
        """Fetch and parse a single product page."""
        html = self.web.product_page(path)
        return parse_product(html)

    def all_plants(self):
        """Yield (path, converted plant data) for all products."""
        for path in self.product_paths():
            raw = self.get_plant(path)
            if raw is None or raw["scientific name"] is None:
                continue

            converted = self.converter.convert(raw)
            converted["scientific name"] = raw["scientific name"]

            common_name = raw["common name"]
            if common_name:
                converted[f"common name/{common_name}"] = True

            yield path, converted


@define(frozen=True)
class SDPIngestor:
    """Ingestor for La Société des Plantes."""

    name: str
    title: str = "La Société des Plantes"
    model: SDPModel = field(factory=SDPModel)
    priority: Priority = field(factory=Priority)

    @classmethod
    def from_config(cls, config, name):
        """Instantiate SDPIngestor from config."""
        model = SDPModel().with_cache(config.storage)
        priority = LocationPriority("Quebec").with_cache(config.storage)
        return cls(name, model=model, priority=priority)

    @logged_fetch
    def fetch_all(self):
        for path, plant in self.model.all_plants():
            yield IngestorPlant(
                plant,
                self.priority.weight,
                ingestor=self.name,
                title=self.title,
                source=self.model.web.source_url(path),
            )
