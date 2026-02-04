import * as THREE from 'three';

export const ROOM_SIZE = 200;

export function addRoom(scene) {
    const wallMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, side: THREE.DoubleSide });

    const floor = new THREE.Mesh(
        new THREE.PlaneGeometry(ROOM_SIZE, ROOM_SIZE),
        wallMaterial
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = 0;
    scene.add(floor);

    const ceiling = new THREE.Mesh(
        new THREE.PlaneGeometry(ROOM_SIZE, ROOM_SIZE),
        wallMaterial
    );
    ceiling.rotation.x = Math.PI / 2;
    ceiling.position.y = ROOM_SIZE;
    scene.add(ceiling);

    const northWall = new THREE.Mesh(
        new THREE.PlaneGeometry(ROOM_SIZE, ROOM_SIZE),
        wallMaterial
    );
    northWall.position.z = -ROOM_SIZE / 2;
    northWall.position.y = ROOM_SIZE / 2;
    scene.add(northWall);

    const southWall = new THREE.Mesh(
        new THREE.PlaneGeometry(ROOM_SIZE, ROOM_SIZE),
        wallMaterial
    );
    southWall.rotation.y = Math.PI;
    southWall.position.z = ROOM_SIZE / 2;
    southWall.position.y = ROOM_SIZE / 2;
    scene.add(southWall);

    const eastWall = new THREE.Mesh(
        new THREE.PlaneGeometry(ROOM_SIZE, ROOM_SIZE),
        wallMaterial
    );
    eastWall.rotation.y = -Math.PI / 2;
    eastWall.position.x = ROOM_SIZE / 2;
    eastWall.position.y = ROOM_SIZE / 2;
    scene.add(eastWall);

    const westWall = new THREE.Mesh(
        new THREE.PlaneGeometry(ROOM_SIZE, ROOM_SIZE),
        wallMaterial
    );
    westWall.rotation.y = Math.PI / 2;
    westWall.position.x = -ROOM_SIZE / 2;
    westWall.position.y = ROOM_SIZE / 2;
    scene.add(westWall);
}

export function addLights(scene) {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.4);
    directionalLight.position.set(5, 10, 5);
    scene.add(directionalLight);
}
