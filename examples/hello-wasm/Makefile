# Convenience targets for the hello-wasm example.
# Requires: Docker Desktop 4.15+ with WASM support enabled (run `wasmdock doctor`).

.PHONY: doctor build run logs stop bench clean

doctor:        ## Verify the Docker WASM environment is ready
	wasmdock doctor

build:         ## Compile to wasm32-wasip1 and package as a scratch image
	wasmdock build

run:           ## Start the WASM container on http://localhost:8080
	wasmdock run --port 8080

logs:          ## Tail logs from the running container
	wasmdock logs --tail 100

stop:          ## Stop and remove the container
	wasmdock stop

bench:         ## Benchmark against an nginx:alpine Linux baseline
	wasmdock bench --iterations 50 --compare-linux nginx:alpine --output report.html

clean:         ## Remove build artifacts and the generated report
	rm -rf target report.html
