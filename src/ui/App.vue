<template>
  <div class="flex flex-col h-screen bg-white">
    <!-- Title Bar -->
    <header class="bg-white text-black p-4 border-b border-gray-200">
      <h1 class="text-xl font-normal">IOSYS</h1>
    </header>

    <!-- Main Content Area -->
    <div class="flex flex-1 overflow-hidden">
      <!-- Left Sidebar -->
      <aside class="w-108 max-w-40% bg-white border-r border-gray-200 p-4 flex flex-col">
        <div class="flex-1">
          <!-- Sidebar content will go here -->
        </div>

        <!-- Input and Submit Button -->
        <div class="mt-4">
          <input type="text"
            class="w-full border border-gray-200 rounded-md p-2 mb-3 focus:outline-none focus:border-black transition-colors duration-150"
            placeholder="Enter text..." />
          <button
            class="w-full bg-black hover:bg-gray-800 text-white font-normal py-2 px-4 rounded-md transition duration-150">
            Submit
          </button>
        </div>
      </aside>

      <!-- Right Main Content -->
      <main class="flex-1 bg-white p-6">
        <!-- Main content will go here -->
      </main>
    </div>
  </div>
</template>
