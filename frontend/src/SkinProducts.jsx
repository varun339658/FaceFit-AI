import { useEffect, useState } from "react";

export default function SkinProducts({ user }) {

  const [products,setProducts] = useState([]);

  useEffect(()=>{

    fetch("http://localhost:5000/skin-products",{
      method:"POST",
      headers:{
        "Content-Type":"application/json"
      },
      body:JSON.stringify(user)
    })
    .then(res=>res.json())
    .then(data=>{
      setProducts(data.products)
    })

  },[user])

  return (

    <div style={{padding:40}}>

      <h1>Recommended Skincare Products</h1>

      <div style={{
        display:"grid",
        gridTemplateColumns:"repeat(3,1fr)",
        gap:30
      }}>

        {products.map((p,i)=>(
          <div key={i} style={{
            border:"1px solid #ddd",
            borderRadius:10,
            padding:20
          }}>

            <img
              src={p.image}
              alt={p.name}
              style={{width:"100%"}}
            />

            <h3>{p.name}</h3>

            <p>{p.price}</p>

            <p>{p.source}</p>

            <a
              href={p.link}
              target="_blank"
              rel="noreferrer"
            >
              Buy Product
            </a>

          </div>
        ))}

      </div>

    </div>

  )
}