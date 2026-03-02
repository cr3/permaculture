"""Unit tests for the La Société des Plantes module."""

from textwrap import dedent
from unittest.mock import Mock

import pytest

from permaculture.database import DatabasePlant
from permaculture.sdp import (
    SDPConverter,
    SDPIngestor,
    SDPModel,
    SDPWeb,
    parse_family,
    parse_product,
    parse_scientific_name,
    parse_sitemap_urls,
)

from .stubs import StubRequestsResponse

SITEMAP_XML = dedent(
    """\
    <?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url>
        <loc>https://www.lasocietedesplantes.com/shop/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/en/shop/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/ashwagandha/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/en/products/ashwagandha-3/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/bourrache-blanche/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/certificat-cadeau-50/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/livre-les-mots-de-la-terre/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/kit-balcon-potager/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/atelier-gourmand-du-jardin-a-la-table-100-tomate/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/t-shirt-amamus-semina/</loc>
      </url>
      <url>
        <loc>https://www.lasocietedesplantes.com/produits/affiche-tomates/</loc>
      </url>
    </urlset>
"""
)

PRODUCT_HTML = dedent(
    """\
    <html>
    <body>
    <h1 class="product_title">bourrache à fleurs blanches bio</h1>
    <div class="woocommerce-product-details__short-description">
    <p>Borago officinalis alba, Boraginacées</p>
    <p>La bourrache à fleurs blanches est un excellent légume-feuille.</p>
    </div>
    <div id="tab-description">
    <p>Annuelle à croissance rapide, la bourrache blanche est un excellent
    légume-feuille au goût de concombre.</p>
    </div>
    </body>
    </html>
"""
)

PRODUCT_HTML_NO_SCIENTIFIC = dedent(
    """\
    <html>
    <body>
    <h1 class="product_title">kit Balcon potager</h1>
    <div class="woocommerce-product-details__short-description">
    <p>Un kit complet pour votre balcon.</p>
    </div>
    </body>
    </html>
"""
)


def test_parse_sitemap_urls():
    """Sitemap should extract only French product URLs, filtering non-plants."""
    urls = parse_sitemap_urls(SITEMAP_XML)
    assert urls == [
        "/produits/ashwagandha/",
        "/produits/bourrache-blanche/",
    ]


def test_parse_sitemap_urls_no_non_plants():
    """Non-plant URLs should be excluded from sitemap results."""
    urls = parse_sitemap_urls(SITEMAP_XML)
    excluded_slugs = [
        "certificat-cadeau-50",
        "livre-les-mots-de-la-terre",
        "kit-balcon-potager",
        "atelier-gourmand-du-jardin-a-la-table-100-tomate",
        "t-shirt-amamus-semina",
        "affiche-tomates",
    ]
    for slug in excluded_slugs:
        assert not any(slug in url for url in urls)


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            "Withania somnifera, Solanacées",
            "withania somnifera",
            id="simple binomial",
        ),
        pytest.param(
            "Borago officinalis alba, Boraginacées",
            "borago officinalis alba",
            id="trinomial",
        ),
        pytest.param(
            "Achillea millefolium, Astéracées",
            "achillea millefolium",
            id="another binomial",
        ),
        pytest.param(
            "No match here",
            None,
            id="no match",
        ),
        pytest.param(
            "",
            None,
            id="empty",
        ),
    ],
)
def test_parse_scientific_name(text, expected):
    """Scientific name should be extracted from description lines."""
    result = parse_scientific_name(text)
    assert result == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param(
            "Withania somnifera, Solanacées",
            "solanacées",
            id="simple",
        ),
        pytest.param(
            "Borago officinalis alba, Boraginacées",
            "boraginacées",
            id="trinomial",
        ),
        pytest.param(
            "No family here",
            None,
            id="no match",
        ),
    ],
)
def test_parse_family(text, expected):
    """Family should be extracted from description lines."""
    result = parse_family(text)
    assert result == expected


def test_parse_product():
    """Parsing a product page should extract structured fields."""
    result = parse_product(PRODUCT_HTML)
    assert result["common name"] == "bourrache à fleurs blanches bio"
    assert result["scientific name"] == "borago officinalis alba"
    assert result["family"] == "boraginacées"
    assert "concombre" in result["description"]


def test_parse_product_no_title():
    """Parsing a page without a product title should return None."""
    result = parse_product("<html><body><h1>Not a product</h1></body></html>")
    assert result is None


def test_parse_product_no_scientific_name():
    """Products without a scientific name should still parse."""
    result = parse_product(PRODUCT_HTML_NO_SCIENTIFIC)
    assert result is not None
    assert result["scientific name"] is None


def test_sdp_web_product_sitemap():
    """The product sitemap should GET the sitemap XML."""
    session = Mock(get=Mock(return_value=StubRequestsResponse(text="<xml/>")))
    result = SDPWeb(session).product_sitemap()
    session.get.assert_called_once_with("/product-sitemap.xml")
    assert result == "<xml/>"


def test_sdp_web_product_page():
    """A product page should GET the given path."""
    session = Mock(get=Mock(return_value=StubRequestsResponse(text="<html/>")))
    result = SDPWeb(session).product_page("/produits/test/")
    session.get.assert_called_once_with("/produits/test/")
    assert result == "<html/>"


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            ("family", "solanacées"),
            [("family", "solanacées")],
            id="family",
        ),
        pytest.param(
            ("description", "Some text"),
            [("description", "some text")],
            id="description",
        ),
        pytest.param(
            ("common name", "test"),
            [],
            id="common name ignored",
        ),
    ],
)
def test_sdp_converter_convert_item(item, expected):
    """Converting items should dispatch to the correct handler."""
    result = SDPConverter().convert_item(*item)
    assert result == expected


def test_sdp_model_product_paths():
    """Product paths should come from the sitemap."""
    web = Mock(product_sitemap=Mock(return_value=SITEMAP_XML))
    paths = SDPModel(web).product_paths()
    assert "/produits/ashwagandha/" in paths
    assert "/produits/bourrache-blanche/" in paths


def test_sdp_model_all_plants():
    """All plants should yield converted data for valid products."""
    web = Mock(
        product_sitemap=Mock(return_value=SITEMAP_XML),
        product_page=Mock(return_value=PRODUCT_HTML),
    )
    model = SDPModel(web)
    plants = list(model.all_plants())

    assert len(plants) == 2
    assert plants[0]["scientific name"] == "borago officinalis alba"
    assert "common name/bourrache à fleurs blanches bio" in plants[0]
    assert "concombre" in plants[0]["description"]


def test_sdp_model_all_plants_skips_no_scientific_name():
    """Plants without a scientific name should be skipped."""

    def product_page(path):
        if "ashwagandha" in path:
            return PRODUCT_HTML
        return PRODUCT_HTML_NO_SCIENTIFIC

    web = Mock(
        product_sitemap=Mock(return_value=SITEMAP_XML),
        product_page=Mock(side_effect=product_page),
    )
    model = SDPModel(web)
    plants = list(model.all_plants())

    # Only ashwagandha and bourrache-blanche from sitemap; both return
    # PRODUCT_HTML for ashwagandha, PRODUCT_HTML_NO_SCIENTIFIC for others.
    # But the sitemap only has 2 plant URLs: ashwagandha, bourrache-blanche.
    # ashwagandha -> PRODUCT_HTML (has sci name) -> kept
    # bourrache-blanche -> PRODUCT_HTML_NO_SCIENTIFIC -> skipped
    assert len(plants) == 1


def test_sdp_ingestor_fetch_all():
    """Fetching all should return DatabasePlant objects."""
    model = Mock(
        all_plants=Mock(
            return_value=[
                {
                    "scientific name": "borago officinalis alba",
                    "common name/bourrache à fleurs blanches bio": True,
                    "family": "boraginacées",
                    "description": "Un excellent légume-feuille.",
                },
            ]
        )
    )

    ingestor = SDPIngestor(model)
    elements = list(ingestor.fetch_all())
    assert elements == [
        DatabasePlant(
            {
                "scientific name": "borago officinalis alba",
                "common name/bourrache à fleurs blanches bio": True,
                "family": "boraginacées",
                "description": "Un excellent légume-feuille.",
            }
        ),
    ]
