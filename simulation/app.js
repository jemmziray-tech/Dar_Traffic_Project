// DOM Elements
const canvasContainer = document.getElementById('canvas-container');
const timeBtns = document.querySelectorAll('.time-btn');
const weatherBtns = document.querySelectorAll('.weather-btn');
const aiToggle = document.getElementById('ai-toggle');
const statusText = document.getElementById('system-status');
const qNS = document.getElementById('q-ns');
const qEW = document.getElementById('q-ew');
const mobileToggle = document.getElementById('mobile-toggle');
const uiPanel = document.getElementById('ui-panel');

// Mobile UI Toggle
mobileToggle.addEventListener('click', () => {
    uiPanel.classList.toggle('show');
});

// Simulation State
let config = {
    timeOfDay: 'morning', // morning, midday, evening
    weather: 'clear', // clear, rainy
    aiEnabled: false,
    baseSpeed: 0.15,
    spawnRateNS: 0.05,
    spawnRateEW: 0.02
};

// Update Config based on UI
function updateConfig() {
    // Time config
    if (config.timeOfDay === 'morning') {
        config.spawnRateNS = 0.08; // Heavy inbound
        config.spawnRateEW = 0.02;
        scene.background = new THREE.Color(0x87CEEB); // Morning sky
        ambientLight.intensity = 0.6;
    } else if (config.timeOfDay === 'midday') {
        config.spawnRateNS = 0.03;
        config.spawnRateEW = 0.03;
        scene.background = new THREE.Color(0x4CA1AF); // Bright sky
        ambientLight.intensity = 1.0;
    } else if (config.timeOfDay === 'evening') {
        config.spawnRateNS = 0.02;
        config.spawnRateEW = 0.08; // Heavy outbound
        scene.background = new THREE.Color(0x2C3E50); // Dusk
        ambientLight.intensity = 0.3;
    }

    // Weather config
    if (config.weather === 'rainy') {
        config.baseSpeed = 0.08; // Slower in rain
        scene.fog = new THREE.FogExp2(0x334455, 0.015);
        rainSystem.visible = true;
    } else {
        config.baseSpeed = 0.15;
        scene.fog = null;
        rainSystem.visible = false;
    }

    // AI config
    if (config.aiEnabled) {
        statusText.textContent = "AI Sensor Active. Prioritizing heaviest congestion.";
        statusText.style.color = "#2ED573";
    } else {
        statusText.textContent = "Fixed 10-second cycles. Prone to gridlock.";
        statusText.style.color = "#FFA502";
    }
}

// UI Event Listeners
timeBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        timeBtns.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        config.timeOfDay = e.target.dataset.time;
        updateConfig();
    });
});

weatherBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
        weatherBtns.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        config.weather = e.target.dataset.weather;
        updateConfig();
    });
});

aiToggle.addEventListener('change', (e) => {
    config.aiEnabled = e.target.checked;
    updateConfig();
});

// --- THREE.JS SETUP ---
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x87CEEB);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 1000);
camera.position.set(-40, 50, 50);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
canvasContainer.appendChild(renderer.domElement);

// Lights
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(20, 50, 20);
dirLight.castShadow = true;
scene.add(dirLight);

// --- CITY ENVIRONMENT ---
// Ground
const groundGeo = new THREE.PlaneGeometry(200, 200);
const groundMat = new THREE.MeshLambertMaterial({ color: 0x223322 });
const ground = new THREE.Mesh(groundGeo, groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// Roads
const roadMat = new THREE.MeshLambertMaterial({ color: 0x333333 });
const roadNSGeo = new THREE.PlaneGeometry(12, 200);
const roadNS = new THREE.Mesh(roadNSGeo, roadMat);
roadNS.rotation.x = -Math.PI / 2;
roadNS.position.y = 0.1;
roadNS.receiveShadow = true;
scene.add(roadNS);

const roadEWGeo = new THREE.PlaneGeometry(200, 12);
const roadEW = new THREE.Mesh(roadEWGeo, roadMat);
roadEW.rotation.x = -Math.PI / 2;
roadEW.position.y = 0.11;
roadEW.receiveShadow = true;
scene.add(roadEW);

// Intersection highlight
const intGeo = new THREE.PlaneGeometry(12, 12);
const intMat = new THREE.MeshLambertMaterial({ color: 0x444444 });
const intersection = new THREE.Mesh(intGeo, intMat);
intersection.rotation.x = -Math.PI / 2;
intersection.position.y = 0.12;
scene.add(intersection);

// Rain Particle System
const rainCount = 1500;
const rainGeo = new THREE.BufferGeometry();
const rainDropPositions = new Float32Array(rainCount * 3);
for(let i=0;i<rainCount;i++) {
    rainDropPositions[i*3] = Math.random() * 100 - 50;
    rainDropPositions[i*3+1] = Math.random() * 50;
    rainDropPositions[i*3+2] = Math.random() * 100 - 50;
}
rainGeo.setAttribute('position', new THREE.BufferAttribute(rainDropPositions, 3));
const rainMat = new THREE.PointsMaterial({
    color: 0xaaaaaa,
    size: 0.1,
    transparent: true,
    opacity: 0.6
});
const rainSystem = new THREE.Points(rainGeo, rainMat);
rainSystem.visible = false; // Hidden initially
scene.add(rainSystem);

// --- TRAFFIC LOGIC ---
let lights = {
    NS: 'green',
    EW: 'red'
};

// Traffic Light Visuals
function createTrafficLight(x, z) {
    const group = new THREE.Group();
    const poleGeo = new THREE.CylinderGeometry(0.2, 0.2, 4);
    const poleMat = new THREE.MeshLambertMaterial({color: 0x111111});
    const pole = new THREE.Mesh(poleGeo, poleMat);
    pole.position.y = 2;
    group.add(pole);

    const boxGeo = new THREE.BoxGeometry(1, 2.5, 1);
    const boxMat = new THREE.MeshLambertMaterial({color: 0x222222});
    const box = new THREE.Mesh(boxGeo, boxMat);
    box.position.y = 4;
    group.add(box);

    const lightGeo = new THREE.SphereGeometry(0.3);
    const redMat = new THREE.MeshBasicMaterial({color: 0x330000});
    const greenMat = new THREE.MeshBasicMaterial({color: 0x003300});
    
    const redLight = new THREE.Mesh(lightGeo, redMat);
    redLight.position.set(0, 4.6, 0.55);
    group.add(redLight);
    
    const greenLight = new THREE.Mesh(lightGeo, greenMat);
    greenLight.position.set(0, 3.4, 0.55);
    group.add(greenLight);

    group.position.set(x, 0, z);
    scene.add(group);
    
    return { red: redLight, green: greenLight };
}

const tlN = createTrafficLight(-8, -8);
const tlS = createTrafficLight(8, 8);
const tlE = createTrafficLight(8, -8);
const tlW = createTrafficLight(-8, 8);

function updateLightVisuals() {
    const redOn = new THREE.MeshBasicMaterial({color: 0xff0000});
    const redOff = new THREE.MeshBasicMaterial({color: 0x330000});
    const greenOn = new THREE.MeshBasicMaterial({color: 0x00ff00});
    const greenOff = new THREE.MeshBasicMaterial({color: 0x003300});

    // NS
    tlN.red.material = tlS.red.material = lights.NS === 'red' ? redOn : redOff;
    tlN.green.material = tlS.green.material = lights.NS === 'green' ? greenOn : greenOff;

    // EW
    tlE.red.material = tlW.red.material = lights.EW === 'red' ? redOn : redOff;
    tlE.green.material = tlW.green.material = lights.EW === 'green' ? greenOn : greenOff;
}

// Car Class
const cars = [];
const carGeo = new THREE.BoxGeometry(2, 1.2, 4);

class Car {
    constructor(direction) {
        this.direction = direction; // 'N', 'S', 'E', 'W'
        this.color = Math.random() > 0.5 ? 0xffffff : (Math.random() > 0.5 ? 0xcc0000 : 0x0000cc);
        const mat = new THREE.MeshLambertMaterial({ color: this.color });
        this.mesh = new THREE.Mesh(carGeo, mat);
        this.mesh.castShadow = true;
        
        this.speed = 0;
        this.maxSpeed = config.baseSpeed + (Math.random() * 0.05);
        this.isStopped = false;

        // Start positions
        const startDist = 60;
        const laneOffset = 2.5;

        if (direction === 'N') { // Coming from North, heading South
            this.mesh.position.set(-laneOffset, 0.6, -startDist);
        } else if (direction === 'S') { // Heading North
            this.mesh.position.set(laneOffset, 0.6, startDist);
            this.mesh.rotation.y = Math.PI;
        } else if (direction === 'E') { // Heading West
            this.mesh.position.set(startDist, 0.6, -laneOffset);
            this.mesh.rotation.y = Math.PI / 2;
        } else if (direction === 'W') { // Heading East
            this.mesh.position.set(-startDist, 0.6, laneOffset);
            this.mesh.rotation.y = -Math.PI / 2;
        }

        scene.add(this.mesh);
        cars.push(this);
    }

    update() {
        // Adjust max speed based on weather
        let currentMax = config.baseSpeed;
        
        // Stop line logic
        const stopLine = 12;
        let distToStop = 999;
        let isAtLight = false;

        if (this.direction === 'N' && this.mesh.position.z < -stopLine) {
            distToStop = -stopLine - this.mesh.position.z;
            isAtLight = true;
        } else if (this.direction === 'S' && this.mesh.position.z > stopLine) {
            distToStop = this.mesh.position.z - stopLine;
            isAtLight = true;
        } else if (this.direction === 'E' && this.mesh.position.x > stopLine) {
            distToStop = this.mesh.position.x - stopLine;
            isAtLight = true;
        } else if (this.direction === 'W' && this.mesh.position.x < -stopLine) {
            distToStop = -this.mesh.position.x - stopLine;
            isAtLight = true;
        }

        // Collision detection (don't hit car in front)
        let distToCar = 999;
        for (let other of cars) {
            if (other !== this && other.direction === this.direction) {
                let d = 999;
                if (this.direction === 'N' && other.mesh.position.z > this.mesh.position.z) d = other.mesh.position.z - this.mesh.position.z;
                if (this.direction === 'S' && other.mesh.position.z < this.mesh.position.z) d = this.mesh.position.z - other.mesh.position.z;
                if (this.direction === 'E' && other.mesh.position.x < this.mesh.position.x) d = this.mesh.position.x - other.mesh.position.x;
                if (this.direction === 'W' && other.mesh.position.x > this.mesh.position.x) d = other.mesh.position.x - this.mesh.position.x;
                
                if (d > 0 && d < distToCar) distToCar = d;
            }
        }

        // Check if light is red for this direction
        let lightColor = (this.direction === 'N' || this.direction === 'S') ? lights.NS : lights.EW;
        
        let targetSpeed = currentMax;

        // Brake for light
        if (isAtLight && lightColor === 'red' && distToStop < 20) {
            if (distToStop < 1) targetSpeed = 0;
            else targetSpeed = currentMax * (distToStop / 20);
        }

        // Brake for car in front
        if (distToCar < 8) {
            targetSpeed = 0;
        } else if (distToCar < 15) {
            targetSpeed = Math.min(targetSpeed, currentMax * ((distToCar-8)/7));
        }

        // Accelerate/Decelerate
        if (this.speed < targetSpeed) this.speed += 0.005;
        if (this.speed > targetSpeed) this.speed -= 0.01;
        if (this.speed < 0) this.speed = 0;

        this.isStopped = this.speed < 0.01;

        // Move
        if (this.direction === 'N') this.mesh.position.z += this.speed;
        if (this.direction === 'S') this.mesh.position.z -= this.speed;
        if (this.direction === 'E') this.mesh.position.x -= this.speed;
        if (this.direction === 'W') this.mesh.position.x += this.speed;
    }
}

// Controller Logic
let lightTimer = 0;
let cycleLength = 300; // frames (~5 seconds at 60fps)

function updateTrafficController() {
    // Calculate Queues
    let queueNS = 0;
    let queueEW = 0;

    cars.forEach(car => {
        if (car.isStopped) {
            if (car.direction === 'N' || car.direction === 'S') queueNS++;
            if (car.direction === 'E' || car.direction === 'W') queueEW++;
        }
    });

    // Update UI Metrics
    qNS.textContent = queueNS;
    qEW.textContent = queueEW;
    qNS.style.color = queueNS > 5 ? '#FF4757' : (queueNS > 2 ? '#FFA502' : '#2ED573');
    qEW.style.color = queueEW > 5 ? '#FF4757' : (queueEW > 2 ? '#FFA502' : '#2ED573');

    if (config.aiEnabled) {
        // AI Dynamic Control: Switch if one queue is heavily backing up and current light has been green for min time
        lightTimer++;
        if (lightTimer > 100) { // Min green time
            if (lights.NS === 'green' && queueEW > queueNS + 2) {
                lights.NS = 'red'; lights.EW = 'green'; lightTimer = 0;
            } else if (lights.EW === 'green' && queueNS > queueEW + 2) {
                lights.NS = 'green'; lights.EW = 'red'; lightTimer = 0;
            }
        }
        // Max green time override
        if (lightTimer > 400) {
            if (lights.NS === 'green') { lights.NS = 'red'; lights.EW = 'green'; }
            else { lights.NS = 'green'; lights.EW = 'red'; }
            lightTimer = 0;
        }
    } else {
        // Standard Fixed Timer
        lightTimer++;
        if (lightTimer > cycleLength) {
            if (lights.NS === 'green') { lights.NS = 'red'; lights.EW = 'green'; }
            else { lights.NS = 'green'; lights.EW = 'red'; }
            lightTimer = 0;
        }
    }

    updateLightVisuals();
}

// Spawner
function spawnCars() {
    if (Math.random() < config.spawnRateNS) {
        new Car(Math.random() > 0.5 ? 'N' : 'S');
    }
    if (Math.random() < config.spawnRateEW) {
        new Car(Math.random() > 0.5 ? 'E' : 'W');
    }
}

// --- ANIMATION LOOP ---
function animate() {
    requestAnimationFrame(animate);

    spawnCars();
    updateTrafficController();

    // Move cars and remove off-screen cars
    for (let i = cars.length - 1; i >= 0; i--) {
        cars[i].update();
        if (Math.abs(cars[i].mesh.position.x) > 80 || Math.abs(cars[i].mesh.position.z) > 80) {
            scene.remove(cars[i].mesh);
            cars.splice(i, 1);
        }
    }

    // Animate rain
    if (config.weather === 'rainy') {
        const positions = rainSystem.geometry.attributes.position.array;
        for(let i=1; i<rainCount*3; i+=3) {
            positions[i] -= 0.5; // fall down
            if (positions[i] < 0) {
                positions[i] = 50; // reset to top
            }
        }
        rainSystem.geometry.attributes.position.needsUpdate = true;
    }

    renderer.render(scene, camera);
}

// Handle Window Resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Initialize
updateConfig();
updateLightVisuals();
animate();
