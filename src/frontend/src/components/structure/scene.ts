import * as THREE from 'three'

import type { LessonStructure, StructureStep } from './model'
import { GROUP_COLORS, STRUCTURE_COLORS } from './palette'

export type StructureFocusKind = 'step' | 'goal' | 'evidence'

export interface StructureFocus {
  kind: StructureFocusKind
  /** 稳定键；2D/3D 与结构清单共用它高亮同一项。 */
  key?: string
  title: string
  text: string
  step?: StructureStep
}

export interface StructureSceneOptions {
  reducedMotion: boolean
  autoRotate: boolean
  onReady: () => void
  onHover: (focus: StructureFocus | null) => void
  onError: (error: unknown) => void
}

export interface StructureSceneHandle {
  dispose: () => void
  resize: () => void
  resetView: () => void
  setAutoRotate: (value: boolean) => void
}

interface Assembly {
  group: THREE.Group
  targetY: number
  delay: number
}

const BASE_Y = -1.7
const FLOW_Y = 0.55
const GOALS_Y = 2.4
const EVIDENCE_Y = -0.8
const SHEET_WIDTH = 6.4
const SHEET_DEPTH = 3.6
const FRUSTUM = 6.4

function easeOutCubic(value: number): number {
  return 1 - Math.pow(1 - Math.min(1, Math.max(0, value)), 3)
}

export function createStructureScene(
  host: HTMLElement,
  structure: LessonStructure,
  options: StructureSceneOptions,
): StructureSceneHandle {
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'low-power',
    // Playwright fullPage 截图会触发合成 resize；保留缓冲避免截图为空。
    preserveDrawingBuffer: true,
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.domElement.className = 'structure-canvas__webgl'
  renderer.domElement.setAttribute('aria-hidden', 'true')
  host.appendChild(renderer.domElement)

  const scene = new THREE.Scene()
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100)
  camera.position.set(8.2, 4.8, 9.4)
  camera.lookAt(0, 0.35, 0)

  const root = new THREE.Group()
  root.rotation.set(0, -0.32, 0)
  scene.add(root)

  scene.add(new THREE.HemisphereLight(0xffffff, 0x5b6a60, 1.9))
  scene.add(new THREE.AmbientLight(0xffffff, 0.32))
  const key = new THREE.DirectionalLight(0xffffff, 1.8)
  key.position.set(6, 9, 7)
  scene.add(key)

  const assemblies: Assembly[] = []
  const flowMeshes: THREE.Mesh[] = []
  const goalMeshes: THREE.Mesh[] = []
  const evidenceMeshes: THREE.Mesh[] = []
  const hitMeshes: THREE.Mesh[] = []
  const focusByMesh = new Map<THREE.Mesh, StructureFocus>()
  const disposables: { dispose: () => void }[] = []
  const materials: THREE.Material[] = []
  let hoveredFocus: StructureFocus | null = null
  let disposed = false
  let ready = false
  let running = false
  let frame = 0
  let visible = true
  let dragging = false
  let moved = false
  let pointerX = 0
  let pointerY = 0
  let assemblyStart = 0
  let autoRotate = options.autoRotate && !options.reducedMotion
  let resumeTimer = 0
  let lastFrame = 0

  const sheetEdgeMaterial = new THREE.LineBasicMaterial({
    color: STRUCTURE_COLORS.paperEdge,
    transparent: true,
    opacity: 0.95,
  })

  function trackMaterial(material: THREE.Material): THREE.Material {
    materials.push(material)
    return material
  }

  function trackGeometry(geometry: THREE.BufferGeometry): THREE.BufferGeometry {
    disposables.push(geometry)
    return geometry
  }

  function addHitProxy(
    parent: THREE.Group,
    x: number,
    y: number,
    z: number,
    width: number,
    height: number,
    depth: number,
    focus: StructureFocus,
  ): void {
    const geometry = trackGeometry(new THREE.BoxGeometry(width, height, depth))
    const material = trackMaterial(
      new THREE.MeshBasicMaterial({
        transparent: true,
        opacity: 0,
        depthWrite: false,
        colorWrite: false,
      }),
    )
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(x, y, z)
    parent.add(mesh)
    hitMeshes.push(mesh)
    focusByMesh.set(mesh, focus)
  }

  function addSheet(
    parent: THREE.Group,
    width: number,
    depth: number,
    color: string = STRUCTURE_COLORS.paper,
    opacity = 0.16,
  ): void {
    const geometry = trackGeometry(new THREE.BoxGeometry(width, 0.045, depth))
    const material = trackMaterial(
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.92,
        metalness: 0,
        transparent: true,
        opacity,
        depthWrite: false,
        side: THREE.DoubleSide,
      }),
    )
    const mesh = new THREE.Mesh(geometry, material)
    parent.add(mesh)

    const edges = trackGeometry(new THREE.EdgesGeometry(geometry))
    const lines = new THREE.LineSegments(edges, sheetEdgeMaterial)
    parent.add(lines)
  }

  function addLayer(targetY: number, delay: number): THREE.Group {
    const group = new THREE.Group()
    group.position.y = targetY
    root.add(group)
    if (!options.reducedMotion) {
      group.position.y = targetY - 0.32
      assemblies.push({ group, targetY, delay })
    }
    return group
  }

  // 底座
  const base = new THREE.Group()
  base.position.y = BASE_Y
  root.add(base)
  addSheet(base, SHEET_WIDTH + 0.4, SHEET_DEPTH + 0.4, '#EDF0E8', 0.6)

  // 证据层
  const evidenceLayer = addLayer(EVIDENCE_Y, 180)
  addSheet(evidenceLayer, SHEET_WIDTH, SHEET_DEPTH, '#F7F8F3', 0.16)
  structure.evidence.forEach((item, index) => {
    const size = 0.4
    const geometry = trackGeometry(new THREE.BoxGeometry(size, 0.1, size))
    const color = item.ok ? STRUCTURE_COLORS.evidenceOk : STRUCTURE_COLORS.evidenceMissing
    const material = trackMaterial(
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.72,
        metalness: item.ok ? 0.12 : 0,
        transparent: !item.ok,
        opacity: item.ok ? 1 : 0.28,
      }),
    )
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(-2.4 + index * 1.2, 0.07, 0.55)
    mesh.userData.evidenceIndex = index
    evidenceLayer.add(mesh)
    evidenceMeshes.push(mesh)
    const evidenceFocus: StructureFocus = {
      kind: 'evidence',
      key: `evidence:${item.key}`,
      title: `证据链 / ${item.label}`,
      text: item.ok ? item.reason || '通过' : `缺项：${item.reason || '未通过'}`,
    }
    focusByMesh.set(mesh, evidenceFocus)
    addHitProxy(evidenceLayer, -2.4 + index * 1.2, 0.16, 0.55, 0.8, 0.4, 0.8, evidenceFocus)
  })
  const evidencePassed = structure.evidence.filter((item) => item.ok).length
  addHitProxy(evidenceLayer, 0, -0.02, 0, 5.8, 0.12, 3.0, {
    kind: 'evidence',
    title: '证据链',
    text: structure.evidence.length
      ? `${evidencePassed} / ${structure.evidence.length} 项通过；悬停/点击方块查看单项`
      : '未接入审查证据',
  })

  // 流程层
  const flowLayer = addLayer(FLOW_Y, 90)
  addSheet(flowLayer, SHEET_WIDTH, SHEET_DEPTH, '#F3F7EE', 0.14)
  const count = Math.max(structure.steps.length, 1)
  const barWidth = 0.5
  const gap = (5.4 - barWidth * count) / Math.max(count - 1, 1)
  structure.steps.forEach((step, index) => {
    const height = 0.22 + (step.minutes / 45) * 0.95
    const geometry = trackGeometry(new THREE.BoxGeometry(barWidth, height, 0.62))
    const baseColor = GROUP_COLORS[step.group]
    const material = trackMaterial(
      new THREE.MeshStandardMaterial({
        color: baseColor,
        roughness: 0.78,
        metalness: 0,
        transparent: step.minutes === 0,
        opacity: step.minutes === 0 ? 0.3 : 1,
        emissive: new THREE.Color(0x000000),
      }),
    )
    const mesh = new THREE.Mesh(geometry, material)
    const x = -2.7 + index * (barWidth + gap)
    mesh.position.set(x, 0.04 + height / 2, 0)
    mesh.userData.stepIndex = index
    flowLayer.add(mesh)
    flowMeshes.push(mesh)
    focusByMesh.set(mesh, {
      kind: 'step',
      key: `step:${step.key}`,
      title: step.title,
      text: step.evidence || `${step.minutes} 分钟`,
      step,
    })
  })

  // 目标层
  const goalsLayer = addLayer(GOALS_Y, 0)
  addSheet(goalsLayer, SHEET_WIDTH, SHEET_DEPTH, '#F4EFE3', 0.2)
  const goalWidths = [1.15, 1.25, 1.05]
  goalWidths.forEach((width, index) => {
    const geometry = trackGeometry(new THREE.BoxGeometry(width, 0.16, 0.55))
    const material = trackMaterial(
      new THREE.MeshStandardMaterial({
        color: STRUCTURE_COLORS.goal,
        roughness: 0.62,
        metalness: 0.18,
      }),
    )
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.set(-1.85 + index * 1.85, 0.11, 0)
    mesh.userData.goalIndex = index
    goalsLayer.add(mesh)
    goalMeshes.push(mesh)
    const goal = [
      { key: 'knowledge', label: '知识目标', text: structure.goals.knowledge },
      { key: 'ability', label: '能力目标', text: structure.goals.ability },
      { key: 'quality', label: '素质目标', text: structure.goals.quality },
    ][index]
    const goalFocus: StructureFocus = {
      kind: 'goal',
      key: `goal:${goal?.key ?? index}`,
      title: `三维目标 / ${goal?.label ?? '目标'}`,
      text: goal?.text || '未填写',
    }
    focusByMesh.set(mesh, goalFocus)
    addHitProxy(goalsLayer, -1.85 + index * 1.85, 0.16, 0, 1.6, 0.5, 0.8, goalFocus)
  })

  // 四角连接柱
  const postHeight = GOALS_Y - BASE_Y
  const postGeometry = trackGeometry(new THREE.BoxGeometry(0.04, postHeight, 0.04))
  const postMaterial = trackMaterial(
    new THREE.MeshStandardMaterial({
      color: STRUCTURE_COLORS.post,
      roughness: 0.8,
      transparent: true,
      opacity: 0.55,
    }),
  )
  for (const x of [-SHEET_WIDTH / 2 + 0.16, SHEET_WIDTH / 2 - 0.16]) {
    for (const z of [-SHEET_DEPTH / 2 + 0.16, SHEET_DEPTH / 2 - 0.16]) {
      const post = new THREE.Mesh(postGeometry, postMaterial)
      post.position.set(x, BASE_Y + postHeight / 2, z)
      root.add(post)
    }
  }

  function resize(): void {
    const width = Math.max(host.clientWidth, 1)
    const height = Math.max(host.clientHeight, 1)
    const aspect = width / height
    camera.left = (-FRUSTUM * aspect) / 2
    camera.right = (FRUSTUM * aspect) / 2
    camera.top = FRUSTUM / 2
    camera.bottom = -FRUSTUM / 2
    camera.updateProjectionMatrix()
    renderer.setSize(width, height, false)
    render()
  }

  function render(): void {
    if (disposed) return
    renderer.render(scene, camera)
    if (!ready) {
      ready = true
      options.onReady()
    }
  }

  function setHovered(focus: StructureFocus | null): void {
    if (focus === hoveredFocus) return
    hoveredFocus = focus
    const meshes = [...flowMeshes, ...goalMeshes, ...evidenceMeshes, ...hitMeshes]
    meshes.forEach((mesh) => {
      const material = mesh.material as THREE.MeshStandardMaterial
      if (!(material instanceof THREE.MeshStandardMaterial)) return
      if (focus && focusByMesh.get(mesh) === focus) {
        material.emissive.set(STRUCTURE_COLORS.hover)
        material.emissiveIntensity = 0.4
      } else {
        material.emissive.set(0x000000)
        material.emissiveIntensity = 0
      }
    })
    options.onHover(focus)
    render()
  }

  function pick(event: PointerEvent): StructureFocus | null {
    const rect = renderer.domElement.getBoundingClientRect()
    if (!rect.width || !rect.height) return null
    const raycaster = new THREE.Raycaster()
    const point = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    )
    raycaster.setFromCamera(point, camera)
    const hits = raycaster.intersectObjects(
      [...flowMeshes, ...goalMeshes, ...evidenceMeshes, ...hitMeshes],
      false,
    )
    if (!hits.length) return null
    return focusByMesh.get(hits[0].object as THREE.Mesh) ?? null
  }

  function rotateBy(dx: number, dy: number): void {
    root.rotation.y += dx;
    root.rotation.x = THREE.MathUtils.clamp(root.rotation.x + dy, -0.18, 0.46)
    render()
  }

  function stopAutoRotate(): void {
    window.clearTimeout(resumeTimer)
  }

  function scheduleAutoRotate(): void {
    if (!autoRotate || options.reducedMotion) return
    stopAutoRotate()
    resumeTimer = window.setTimeout(() => {
      if (!disposed && !hoveredFocus && !dragging) {
        autoRotate = true
        lastFrame = 0
      }
    }, 2400)
  }

  function onPointerDown(event: PointerEvent): void {
    if (event.button !== 0) return
    dragging = true
    moved = false
    pointerX = event.clientX
    pointerY = event.clientY
    autoRotate = false
    stopAutoRotate()
    renderer.domElement.setPointerCapture(event.pointerId)
  }

  function onPointerMove(event: PointerEvent): void {
    if (dragging) {
      const dx = event.clientX - pointerX
      const dy = event.clientY - pointerY
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true
      pointerX = event.clientX
      pointerY = event.clientY
      rotateBy(dx * 0.008, dy * 0.005)
      return
    }
    setHovered(pick(event))
  }

  function onPointerUp(event: PointerEvent): void {
    if (!dragging) return
    dragging = false
    if (renderer.domElement.hasPointerCapture(event.pointerId)) {
      renderer.domElement.releasePointerCapture(event.pointerId)
    }
    if (!moved) setHovered(pick(event))
    if (options.autoRotate && !options.reducedMotion) scheduleAutoRotate()
  }

  function onPointerLeave(): void {
    if (!dragging) setHovered(null)
  }

  function tick(now: number): void {
    if (disposed) return
    frame = window.requestAnimationFrame(tick)
    if (lastFrame && now - lastFrame < 32) return
    const delta = lastFrame ? Math.min(now - lastFrame, 64) : 16
    lastFrame = now

    let animating = false
    if (assemblies.length) {
      if (!assemblyStart) assemblyStart = now
      const elapsed = now - assemblyStart
      for (const assembly of assemblies) {
        const progress = easeOutCubic((elapsed - assembly.delay) / 520)
        assembly.group.position.y = assembly.targetY - 0.32 * (1 - progress)
        if (progress < 1) animating = true
      }
      if (!animating) assemblies.length = 0
    }

    if (autoRotate && !dragging && !hoveredFocus) {
      root.rotation.y += (delta / 1000) * 0.16
      animating = true
    }

    if (animating || !ready) render()
  }

  function start(): void {
    if (disposed || running || !visible || document.hidden) return
    running = true
    lastFrame = 0
    frame = window.requestAnimationFrame(tick)
  }

  function stop(): void {
    running = false
    if (frame) window.cancelAnimationFrame(frame)
    frame = 0
  }

  const intersectionObserver =
    typeof IntersectionObserver === 'function'
      ? new IntersectionObserver((entries) => {
          visible = entries.some((entry) => entry.isIntersecting)
          if (visible) start()
          else stop()
        })
      : null
  intersectionObserver?.observe(host)

  function onVisibilityChange(): void {
    if (document.hidden) stop()
    else start()
  }

  function onContextLost(event: Event): void {
    event.preventDefault()
    stop()
    options.onError(new Error('webgl-context-lost'))
  }

  const canvas = renderer.domElement
  canvas.addEventListener('pointerdown', onPointerDown)
  canvas.addEventListener('pointermove', onPointerMove)
  canvas.addEventListener('pointerup', onPointerUp)
  canvas.addEventListener('pointercancel', onPointerUp)
  canvas.addEventListener('pointerleave', onPointerLeave)
  canvas.addEventListener('webglcontextlost', onContextLost)
  document.addEventListener('visibilitychange', onVisibilityChange)

  resize()
  if (options.reducedMotion) {
    for (const assembly of assemblies) assembly.group.position.y = assembly.targetY
    assemblies.length = 0
  }
  render()
  start()

  return {
    dispose(): void {
      if (disposed) return
      disposed = true
      stop()
      stopAutoRotate()
      intersectionObserver?.disconnect()
      document.removeEventListener('visibilitychange', onVisibilityChange)
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('pointerup', onPointerUp)
      canvas.removeEventListener('pointercancel', onPointerUp)
      canvas.removeEventListener('pointerleave', onPointerLeave)
      canvas.removeEventListener('webglcontextlost', onContextLost)
      for (const item of disposables) item.dispose()
      for (const material of materials) material.dispose()
      sheetEdgeMaterial.dispose()
      renderer.dispose()
      renderer.forceContextLoss()
      canvas.remove()
    },
    resize,
    resetView(): void {
      root.rotation.set(0, -0.32, 0)
      render()
    },
    setAutoRotate(value: boolean): void {
      autoRotate = value && !options.reducedMotion
      if (autoRotate) {
        lastFrame = 0
        start()
      } else {
        stopAutoRotate()
      }
    },
  }
}


