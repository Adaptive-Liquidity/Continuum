import { useState } from 'react'
import './App.css'

function App() {
  const [isLive, setIsLive] = useState(false)
  const [activeNode, setActiveNode] = useState('Field')

  const nodes = [
    { name: 'Field', detail: 'collective context', value: '94.8%', color: 'cyan' },
    { name: 'Memory', detail: 'long-horizon recall', value: '12.4k', color: 'violet' },
    { name: 'Signal', detail: 'emergent intent', value: 'live', color: 'orange' },
  ]

  return (
    <main>
      <nav className="nav-shell" aria-label="Primary navigation"><a className="brand" href="#top" aria-label="Continuum home"><span className="brand-mark"><i></i><i></i><i></i></span><span>continuum</span></a><div className="nav-links"><a href="#principles">Principles</a><a href="#substrate">The substrate</a><a href="#signal">Signal</a></div><button className="nav-action" type="button" onClick={() => setIsLive(true)}>Enter the field <span aria-hidden="true">↗</span></button></nav>
      <section className="hero-section" id="top"><div className="hero-copy"><div className="eyebrow"><span className="live-dot"></span> A new layer of operation <span className="eyebrow-line"></span> 001</div><h1>Intelligence<br /><em>without a ceiling.</em></h1><p className="hero-lede">Continuum is the adaptive substrate for a world that no longer waits for systems to catch up.</p><div className="hero-actions"><button className="primary-button" type="button" onClick={() => setIsLive(!isLive)}>{isLive ? 'Field is active' : 'Activate Continuum'} <span aria-hidden="true">{isLive ? '◉' : '→'}</span></button><a className="text-link" href="#substrate">See how it grows <span aria-hidden="true">↓</span></a></div></div><div className="hero-orbit" aria-label="Continuum adaptive field visualization" role="img"><div className="orbit orbit-one"></div><div className="orbit orbit-two"></div><div className="orbit orbit-three"></div><div className="core"><span>∞</span><small>continuum<br />core</small></div><span className="orbit-label label-top">sense</span><span className="orbit-label label-right">adapt</span><span className="orbit-label label-bottom">become</span><span className="orbit-label label-left">heal</span><span className="orbit-node node-a"></span><span className="orbit-node node-b"></span><span className="orbit-node node-c"></span></div><div className="scroll-cue"><span>Scroll to enter</span><span className="scroll-line"></span></div></section>
      <section className="manifesto" id="principles"><p className="section-index">01 / THE PREMISE</p><h2>The old stack was built to <span>contain</span> intelligence.<br />We built what comes after.</h2><div className="manifesto-note"><span className="note-line"></span><p>Not another system to operate.<br /><strong>A living field that operates.</strong></p></div></section>
      <section className="substrate-section" id="substrate"><div className="section-intro"><p className="section-index">02 / THE SUBSTRATE</p><h2>One field.<br /><em>Many minds.</em></h2><p>Continuum turns fragmented infrastructure into a coherent, self-sustaining intelligence. It senses the whole, then makes the next move.</p></div><div className="system-panel"><div className="panel-header"><span><i className="status-dot"></i> CONTINUUM FIELD</span><span className={isLive ? 'panel-live' : ''}>{isLive ? 'LIVE / ADAPTING' : 'STANDBY / READY'}</span></div><div className="field-map"><div className="map-grid"></div><div className="map-rings"><span></span><span></span><span></span></div><div className="map-pulse"></div><div className="map-core">C</div><div className="map-caption">Distributed cognitive architecture<br /><strong>coherence: {isLive ? '99.7' : '94.8'}%</strong></div></div><div className="node-list">{nodes.map((node) => <button className={`node-row ${activeNode === node.name ? 'selected' : ''}`} key={node.name} type="button" onClick={() => setActiveNode(node.name)}><span className={`node-icon ${node.color}`}></span><span className="node-name"><strong>{node.name}</strong><small>{node.detail}</small></span><span className="node-value">{node.value}</span><span className="node-arrow">↗</span></button>)}</div></div></section>
      <section className="signal-section" id="signal"><div className="signal-copy"><p className="section-index">03 / THE SIGNAL</p><h2>Built for the<br /><em>becoming.</em></h2></div><div className="signal-quote"><p>“The most important infrastructure is the one that can change its mind.”</p><span>CONTINUUM / FIELD NOTE 001</span></div></section><footer><a className="brand" href="#top"><span className="brand-mark"><i></i><i></i><i></i></span><span>continuum</span></a><span>Adaptive intelligence for the next world.</span><span>© 2026 / OPEN FIELD</span></footer>
    </main>
  )
}

export default App
