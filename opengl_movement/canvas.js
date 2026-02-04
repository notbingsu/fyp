import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { addLights, addRoom, ROOM_SIZE } from './objects.js';

// Scene setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xcccccc);

// Camera setup (third-person view)
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);

// Renderer setup
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Static objects
addRoom(scene);
addLights(scene);

// Load anatomy model
const gltfLoader = new GLTFLoader();
let anatomyModel = null;
gltfLoader.load(
    './models/anatomy.glb',
    (gltf) => {
        anatomyModel = gltf.scene;
        anatomyModel.scale.set(7, 7, 7);
        anatomyModel.position.set(0, 60, 0);
        scene.add(anatomyModel);
    },
    undefined,
    (error) => {
        console.error('Failed to load anatomy.glb', error);
    }
);

// Cursor (the object player controls)
const cursorGeometry = new THREE.SphereGeometry(0.25, 20, 20);
const cursorMaterial = new THREE.MeshStandardMaterial({ color: 0xff0000 });
const cursor = new THREE.Mesh(cursorGeometry, cursorMaterial);
cursor.position.set(0, 2, 0);
scene.add(cursor);

// Cursor movement properties
const cursorSpeed = 0.5;
let cameraDistance = 5;
const cameraHeight = 2;
const minCameraDistance = 2;
const maxCameraDistance = 30;
const zoomSpeed = 0.05;

// Camera rotation properties
let cameraRotationY = 0; // Horizontal rotation (around Y axis)
let cameraRotationX = 0.3; // Vertical rotation (pitch)
const mouseSensitivity = 0.002;

// Movement state
const keys = {
    w: false,
    a: false,
    s: false,
    d: false
};

// Mouse state
let isMouseDown = false;
let lastMouseX = 0;
let lastMouseY = 0;

// Keyboard event listeners
window.addEventListener('keydown', (e) => {
    const key = e.key.toLowerCase();
    if (key in keys) {
        keys[key] = true;
    }
});

window.addEventListener('keyup', (e) => {
    const key = e.key.toLowerCase();
    if (key in keys) {
        keys[key] = false;
    }
});

// Mouse event listeners for camera control
window.addEventListener('mousedown', (e) => {
    isMouseDown = true;
    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
});

window.addEventListener('mouseup', () => {
    isMouseDown = false;
});

window.addEventListener('mousemove', (e) => {
    if (isMouseDown) {
        const deltaX = e.clientX - lastMouseX;
        const deltaY = e.clientY - lastMouseY;

        // Update camera rotation based on mouse movement
        cameraRotationY -= deltaX * mouseSensitivity;
        cameraRotationX -= deltaY * mouseSensitivity;

        // Clamp vertical rotation to prevent flipping
        cameraRotationX = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, cameraRotationX));

        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
    }
});

// Mouse wheel zoom for camera distance
window.addEventListener('wheel', (e) => {
    e.preventDefault();
    cameraDistance += e.deltaY * zoomSpeed;
    cameraDistance = Math.max(minCameraDistance, Math.min(maxCameraDistance, cameraDistance));
}, { passive: false });

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Update cursor position based on input
function updateCursor() {
    const moveVector = new THREE.Vector3();

    // Calculate forward direction as the ray from camera through cursor
    const forwardDirection = new THREE.Vector3();
    forwardDirection.subVectors(cursor.position, camera.position);
    forwardDirection.normalize();

    // Get right direction (perpendicular to forward direction and world up)
    const rightDirection = new THREE.Vector3();
    rightDirection.crossVectors(forwardDirection, new THREE.Vector3(0, 1, 0));
    rightDirection.normalize();

    // W: Move forward in camera direction (away from camera)
    if (keys.w) {
        moveVector.add(forwardDirection.clone().multiplyScalar(cursorSpeed));
    }

    // S: Move backward (towards camera)
    if (keys.s) {
        moveVector.add(forwardDirection.clone().multiplyScalar(-cursorSpeed));
    }

    // A: Move left
    if (keys.a) {
        moveVector.add(rightDirection.clone().multiplyScalar(-cursorSpeed));
    }

    // D: Move right
    if (keys.d) {
        moveVector.add(rightDirection.clone().multiplyScalar(cursorSpeed));
    }

    // Apply movement
    cursor.position.add(moveVector);

    // Boundary constraints (keep cursor inside room)
    const boundary = ROOM_SIZE / 2 - 1; // Leave some margin
    cursor.position.x = Math.max(-boundary, Math.min(boundary, cursor.position.x));
    cursor.position.z = Math.max(-boundary, Math.min(boundary, cursor.position.z));
    cursor.position.y = Math.max(1, Math.min(ROOM_SIZE - 1, cursor.position.y));
}

// Update camera to follow cursor (third-person view)
function updateCamera() {
    // Calculate camera position based on rotation angles
    const offsetX = Math.sin(cameraRotationY) * Math.cos(cameraRotationX) * cameraDistance;
    const offsetY = Math.sin(cameraRotationX) * cameraDistance + cameraHeight;
    const offsetZ = Math.cos(cameraRotationY) * Math.cos(cameraRotationX) * cameraDistance;

    // Position camera relative to cursor
    camera.position.set(
        cursor.position.x + offsetX,
        cursor.position.y + offsetY,
        cursor.position.z + offsetZ
    );

    // Always look at the cursor
    camera.lookAt(cursor.position);

}

// Animation loop
function animate() {
    requestAnimationFrame(animate);

    updateCursor();
    updateCamera();

    renderer.render(scene, camera);
}

// Initial camera setup
camera.position.set(0, 5, 10);
camera.lookAt(cursor.position);

// Start animation
animate();
