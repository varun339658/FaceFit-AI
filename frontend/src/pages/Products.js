import React, { useEffect, useState } from "react";

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  .products-page {
    min-height: 100vh;
    background: #F7F5F0;
    font-family: 'DM Sans', sans-serif;
    color: #1A1A1A;
    padding: 60px 48px;
  }

  .products-header {
    margin-bottom: 64px;
    border-bottom: 1px solid #D9D4CA;
    padding-bottom: 32px;
  }

  .products-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: clamp(2.2rem, 5vw, 3.5rem);
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #1A1A1A;
  }

  .products-header p {
    margin-top: 10px;
    font-size: 0.95rem;
    color: #7A7468;
    font-weight: 300;
    letter-spacing: 0.03em;
  }

  .category-block {
    margin-bottom: 72px;
  }

  .category-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1A1A1A;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .category-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, #D9D4CA, transparent);
  }

  .products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 24px;
  }

  .product-card {
    background: #FFFFFF;
    border-radius: 4px;
    overflow: hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    cursor: pointer;
    position: relative;
  }

  .product-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 20px 48px rgba(0,0,0,0.10);
  }

  .product-image-wrap {
    width: 100%;
    aspect-ratio: 1 / 1;
    overflow: hidden;
    background: #F0EDE8;
    position: relative;
  }

  .product-image-wrap img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    padding: 20px;
    transition: transform 0.4s ease;
  }

  .product-card:hover .product-image-wrap img {
    transform: scale(1.05);
  }

  .product-body {
    padding: 20px 22px 22px;
    border-top: 1px solid #F0EDE8;
  }

  .product-title {
    font-size: 0.92rem;
    font-weight: 500;
    line-height: 1.45;
    color: #1A1A1A;
    margin-bottom: 10px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .product-price {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #2C5F2E;
    margin-bottom: 16px;
  }

  .buy-btn {
    display: block;
    width: 100%;
    padding: 11px 0;
    background: #1A1A1A;
    color: #F7F5F0;
    text-align: center;
    text-decoration: none;
    font-size: 0.8rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border-radius: 2px;
    transition: background 0.2s ease, color 0.2s ease;
  }

  .buy-btn:hover {
    background: #C8A96E;
    color: #1A1A1A;
  }

  /* Loading skeleton */
  .loading-screen {
    min-height: 100vh;
    background: #F7F5F0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    font-family: 'DM Sans', sans-serif;
  }

  .loading-spinner {
    width: 36px;
    height: 36px;
    border: 2px solid #D9D4CA;
    border-top-color: #1A1A1A;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading-text {
    font-size: 0.85rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #7A7468;
  }

  /* Empty state */
  .empty-state {
    min-height: 100vh;
    background: #F7F5F0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: 'DM Sans', sans-serif;
    gap: 12px;
    color: #7A7468;
  }

  .empty-icon {
    font-size: 2.5rem;
    margin-bottom: 8px;
  }

  .empty-state h3 {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    color: #1A1A1A;
  }

  .empty-state p {
    font-size: 0.9rem;
    font-weight: 300;
  }

  /* Fade-in animation for cards */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .product-card {
    animation: fadeUp 0.4s ease both;
  }

  .product-card:nth-child(1) { animation-delay: 0.05s; }
  .product-card:nth-child(2) { animation-delay: 0.10s; }
  .product-card:nth-child(3) { animation-delay: 0.15s; }
  .product-card:nth-child(4) { animation-delay: 0.20s; }
  .product-card:nth-child(5) { animation-delay: 0.25s; }
  .product-card:nth-child(6) { animation-delay: 0.30s; }
`;

function Products() {
  const [products, setProducts] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const analysis = JSON.parse(localStorage.getItem("faceAnalysis") || "{}");

    fetch("http://127.0.0.1:5000/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(analysis),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch products");
        return res.json();
      })
      .then((data) => {
        setProducts(data.products || {});
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const categories = Object.keys(products);
  const totalCount = categories.reduce((acc, c) => acc + products[c].length, 0);

  return (
    <>
      <style>{styles}</style>

      {loading && (
        <div className="loading-screen">
          <div className="loading-spinner" />
          <p className="loading-text">Curating your picks</p>
        </div>
      )}

      {error && (
        <div className="empty-state">
          <div className="empty-icon">⚠</div>
          <h3>Something went wrong</h3>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && categories.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">✦</div>
          <h3>No products found</h3>
          <p>Try updating your face analysis and refreshing.</p>
        </div>
      )}

      {!loading && !error && categories.length > 0 && (
        <div className="products-page">
          <div className="products-header">
            <h1>Your Recommendations</h1>
            <p>{totalCount} products across {categories.length} {categories.length === 1 ? "category" : "categories"}</p>
          </div>

          {categories.map((category) => (
            <div key={category} className="category-block">
              <h2 className="category-title">{category}</h2>
              <div className="products-grid">
                {products[category].map((p, i) => (
                  <div key={i} className="product-card">
                    <div className="product-image-wrap">
                      <img src={p.image} alt={p.title} loading="lazy" />
                    </div>
                    <div className="product-body">
                      <p className="product-title">{p.title}</p>
                      <p className="product-price">{p.price}</p>
                      <a
                        href={p.link}
                        target="_blank"
                        rel="noreferrer"
                        className="buy-btn"
                      >
                        Buy on Amazon
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

export default Products;