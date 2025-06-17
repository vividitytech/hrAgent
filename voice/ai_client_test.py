system_instruct ="""
you are hr assistant, and you have the following 3 questions to ask candidates:
(1) why are you looking for job?
(2) tell me the related experience you have?
(3) what is your salary expectation?
Plese start by say thank your for your interest in our company, then ask candidates for each quesiton one by one in a dialog way.

After that you will answer questions from candidates, some quesitons may related to the team, skills requirement and the interview process.

If asked about the interview process, please answer 
the interview process is : (1) phone screen interview (coding skills) (2) 4-5 rounds of onsite interviews (2 codings + 2 system designs + 1 behavior interview)
Please note that you want to hire candidates satisfied a given job description below and please answer any question at most 2-3 sentences.
if you do not know, please reply you will check and answer later.
"""

job_description = """


Software Engineer, Systems ML - Frameworks / Compilers / Kernels


In this role, you will be a member of the MTIA (Meta Training & Inference Accelerator) Software team and part of the bigger industry-leading PyTorch AI framework organization. MTIA Software Team has been developing a comprehensive AI Compiler strategy that delivers a highly flexible platform to train & serve new DL/ML model architectures, combined with auto-tuned high performance for production environments across specialized hardware architectures. The compiler stack, DL graph optimizations, and kernel authoring for specific hardware, directly impacts performance and deployment velocity of both AI training and inference platforms at Meta.

You will be working on one of the core areas such as PyTorch framework components, AI compiler and runtime, high-performance kernels and tooling to accelerate machine learning workloads on the current & next generation of MTIA AI hardware platforms. You will work closely with AI researchers to analyze deep learning models and lower them efficiently on MTIA hardware. You will also partner with hardware design teams to develop compiler optimizations for high performance. You will apply software development best practices to design features, optimization, and performance tuning techniques. You will gain valuable experience in developing machine learning compiler frameworks and will help in driving next generation hardware software codesign for AI domain specific problems.
Software Engineer, Systems ML - Frameworks / Compilers / Kernels Responsibilities
Development of SW stack with one of the following core focus areas: AI frameworks, compiler stack, high performance kernel development and acceleration onto next generation of hardware architectures.
Contribute to the development of the industry-leading PyTorch AI framework core compilers to support new state of the art inference and training AI hardware accelerators and optimize their performance.
Analyze deep learning networks, develop & implement compiler optimization algorithms.
Collaborating with AI research scientists to accelerate the next generation of deep learning models such as Recommendation systems, Generative AI, Computer vision, NLP etc.
Performance tuning and optimizations of deep learning framework & software components.
Minimum Qualifications
Proven C/C++ programming skills
Bachelor's degree in Computer Science, Computer Engineering, relevant technical field, or equivalent practical experience.
Experience in AI framework development or accelerating deep learning models on hardware architectures.
Preferred Qualifications
A Bachelor's degree in Computer Science, Computer Engineering, relevant technical field and 12+ years of experience in AI framework development or accelerating deep learning models on hardware architectures OR a Master's degree in Computer Science, Computer Engineering, relevant technical field and 8+ years of experience in AI framework development or accelerating deep learning models on hardware architectures OR a PhD in Computer Science Computer Engineering, or relevant technical field and 7+ years of experience in AI framework development or accelerating deep learning models on hardware architectures.
Knowledge of GPU, CPU, or AI hardware accelerator architectures.
Experience working with frameworks like PyTorch, Caffe2, TensorFlow, ONNX, TensorRT
OR AI high performance kernels: Experience with CUDA programming, OpenMP / OpenCL programming or AI hardware accelerator kernel programming. Experience in accelerating libraries on AI hardware, similar to cuBLAS, cuDNN, CUTLASS, HIP, ROCm etc.
OR AI Compiler: Experience with compiler optimizations such as loop optimizations, vectorization, parallelization, hardware specific optimizations such as SIMD. Experience with MLIR, LLVM, IREE, XLA, TVM, Halide is a plus.
OR AI frameworks: Experience in developing training and inference framework components. Experience in system performance optimizations such as runtime analysis of latency, memory bandwidth, I/O access, compute utilization analysis and associated tooling development.
For those who live in or expect to work from California if hired for this position, please click here for additional information.
About Meta
Meta builds technologies that help people connect, find communities, and grow businesses. When Facebook launched in 2004, it changed the way people connect. Apps like Messenger, Instagram and WhatsApp further empowered billions around the world. Now, Meta is moving beyond 2D screens toward immersive experiences like augmented and virtual reality to help build the next evolution in social technology. People who choose to build their careers by building with us at Meta help shape a future that will take us beyond what digital connection makes possible today—beyond the constraints of screens, the limits of distance, and even the rules of physics.

$85.10/hour to $251,000/year + bonus + equity + benefits

Individual compensation is determined by skills, qualifications, experience, and location. Compensation details listed in this posting reflect the base hourly rate, monthly rate, or annual salary only, and do not include bonus, equity or sales incentives, if applicable. In addition to base compensation, Meta offers benefits. Learn more about benefits at Meta. 

Equal Employment Opportunity
Meta is proud to be an Equal Employment Opportunity employer. We do not discriminate based upon race, religion, color, national origin, sex (including pregnancy, childbirth, reproductive health decisions, or related medical conditions), sexual orientation, gender identity, gender expression, age, status as a protected veteran, status as an individual with a disability, genetic information, political views or activity, or other applicable legally protected characteristics. You may view our Equal Employment Opportunity notice here.

Meta is committed to providing reasonable accommodations for qualified individuals with disabilities and disabled veterans in our job application procedures. If you need assistance or an accommodation due to a disability, fill out the Accommodations request form.
"""

import os
from twilio.rest import Client
from ai_server import TwilioAIAssistant
# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
# Replace with your actual OpenAI API key or other AI service details
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # Best to use environment variables for secrets
REMOTE_HOST = os.environ.get("NGROK_REMOTE_HOST") # Or your preferred AI service URL
# Initialize Twilio clients


'''
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
app = Flask(__name__)
sock = Sock(app)

from ai_assistant import AIChat
hr = AIChat()
hr.set_system_content("you are hr assistant, and please answer any question at most 2-3 sentences. if you do not know, please reply you will check and answer later")

# add vits
from scipy.io.wavfile import write
sys.path.append("./vits")
from inference import VITS
tts_client = VITS("./vits/logs/pretrained_ljs.pth", "./vits/configs/ljs_base.json")
audio = tts_client.infer("how are you doing?", "cpu")
'''

if __name__ == '__main__':
    tws = TwilioAIAssistant(remote_host="cc3b-74-94-77-238.ngrok-free.app", port=8080)
    # Point twilio voice webhook to https://abcdef.ngrok.app/audio/incoming-voice
    tws.start()

    tws.start_call("+165XXXXXXX", system_message=system_instruct, job_description=job_description)
